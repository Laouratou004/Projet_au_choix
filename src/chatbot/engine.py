"""Moteur de dialogue du chatbot.

Le chatbot est une machine à états. Chaque état correspond à une étape
du parcours guidé. `reponse_pour(conversation)` calcule la réponse à
renvoyer en fonction de l'état courant ; `traiter_message(conversation,
action, texte)` fait avancer la conversation vers l'état suivant.

Schéma global des transitions (parcours nominal) :

  ACCUEIL ──"deposer"──> CATEGORIE_DEMANDEE ──choix──> DESCRIPTION_DEMANDEE
     │                          │                              │
     │                          │"suggerer"                    ▼
     │                          ▼                         DETAILS_DEMANDES
     │            DESCRIPTION_POUR_SUGGESTION                  │
     │                          │                              ▼
     │                          ▼                          RECAPITULATIF
     │             SUGGESTION_PROPOSEE  ───────────────────────│
     │                                                          │
     └──"suivre"──> SUIVI_REF_DEMANDEE                  "confirmer"
                                │                               │
                                └─────────> TERMINEE <──────────┘
"""
import unicodedata

from reclamations.models import Reclamation

from .models import Conversation


# ---------------------------------------------------------------------------
# Données statiques : questions complémentaires et mots-clés par catégorie.
# ---------------------------------------------------------------------------

# Questions complémentaires à poser après la description initiale.
# Chaque question est un dict { key, question, exemple }. Les réponses sont
# stockées dans Conversation.contexte['details'][key] puis concaténées à
# la description finale de la Réclamation pour donner du contexte à l'admin.
QUESTIONS_DETAILS = {
    'notes': [
        {'key': 'matiere',     'question': 'Quelle est la matière ou le cours concerné ?',           'exemple': 'ex. Algèbre linéaire'},
        {'key': 'semestre',    'question': 'À quel semestre / année universitaire cela se rapporte-t-il ?', 'exemple': 'ex. Semestre 2, 2025-2026'},
        {'key': 'enseignant',  'question': "Quel est le nom de l'enseignant en charge ?",            'exemple': 'ex. M. Diallo'},
    ],
    'scolarite': [
        {'key': 'document',    'question': 'De quel document ou démarche s’agit-il exactement ?',    'exemple': 'ex. certificat de scolarité, attestation, carte étudiant'},
        {'key': 'depuis_quand','question': 'Depuis quand attendez-vous une réponse ou la délivrance ?', 'exemple': 'ex. depuis 3 semaines'},
    ],
    'examens': [
        {'key': 'examen',      'question': 'De quel examen s’agit-il ?',                              'exemple': 'ex. Examen final de Bases de données'},
        {'key': 'date_examen', 'question': 'À quelle date est-il prévu (ou a-t-il eu lieu) ?',         'exemple': 'ex. 12/06/2026'},
        {'key': 'justificatif','question': 'Avez-vous un justificatif à fournir ? Si oui, lequel ?',  'exemple': 'ex. certificat médical, ou "non"'},
    ],
    'bourse': [
        {'key': 'periode',     'question': 'Quelle période ou mois est concerné ?',                   'exemple': 'ex. Avril 2026'},
        {'key': 'montant',     'question': 'Quel est le montant attendu ?',                           'exemple': 'ex. 350 000 GNF'},
        {'key': 'dossier',     'question': 'Quel est votre numéro de dossier ou de contrat de bourse ?', 'exemple': 'ex. B-2025-1234'},
    ],
}


def _questions_pour(categorie):
    # Renvoie la liste des questions pour une catégorie, ou [] si la
    # catégorie n'a pas de questions définies (cas dégradé).
    return QUESTIONS_DETAILS.get(categorie, [])


def _question_courante(conversation):
    """Renvoie la question en cours (selon details_index) ou None si terminé."""
    questions = _questions_pour(conversation.contexte.get('categorie'))
    idx = conversation.contexte.get('details_index', 0)
    if 0 <= idx < len(questions):
        return questions[idx]
    # Toutes les questions ont été posées → l'étape DETAILS_DEMANDES doit
    # passer au récapitulatif.
    return None


def _formatter_description_complete(conversation):
    """Description initiale + détails formatés pour l'admin."""
    desc = conversation.contexte.get('description', '')
    details = conversation.contexte.get('details', {})
    questions = _questions_pour(conversation.contexte.get('categorie'))
    if not details:
        # Catégorie sans questions complémentaires : on enregistre la
        # description brute.
        return desc
    # Format lisible : description, séparateur, puis chaque précision en
    # bullet point. Ce texte est ce que l'admin voit dans le détail de
    # la réclamation.
    lignes = [desc.strip(), '', '--- Précisions ---']
    for q in questions:
        rep = details.get(q['key'])
        if rep:
            lignes.append(f"• {q['question']} → {rep}")
    return '\n'.join(lignes)


# Mots-clés par catégorie (en minuscules, sans accents). Sert à la
# suggestion automatique de catégorie en S3.2 — bonus.
MOTS_CLES_CATEGORIES = {
    Reclamation.CAT_NOTES: [
        'note', 'notes', 'moyenne', 'copie', 'correction', 'revision',
        'releve de notes', 'calcul', 'saisie',
    ],
    Reclamation.CAT_SCOLARITE: [
        'scolarite', 'releve', 'certificat', 'inscription', 'attestation',
        'informations personnelles', 'dossier', 'carte etudiant',
    ],
    Reclamation.CAT_EXAMENS: [
        'examen', 'examens', 'planning', 'conflit', 'absence', 'rattrapage',
        'salle', 'convocation', 'epreuve',
    ],
    Reclamation.CAT_BOURSE: [
        'bourse', 'versee', 'verser', 'paiement', 'frais', 'scolarite payee',
        'allocation', 'aide financiere',
    ],
}


def _normaliser(texte):
    """Minuscules + suppression des accents pour matcher les mots-clés."""
    # NFD décompose les caractères accentués en caractère + accent ; on
    # retire ensuite tout ce qui appartient à la catégorie "Mn" (mark
    # nonspacing), ce qui élimine les accents.
    sans_accent = unicodedata.normalize('NFD', texte)
    sans_accent = ''.join(c for c in sans_accent if unicodedata.category(c) != 'Mn')
    return sans_accent.lower()


def suggerer_categorie(description):
    """Devine la catégorie la plus probable à partir de la description.

    Renvoie un tuple (categorie, nombre_de_matches). Si aucun mot-clé
    n'est trouvé, renvoie (None, 0).
    """
    texte = _normaliser(description)
    # Approche naïve : on compte les occurrences de mots-clés par catégorie
    # et on retient celle qui en a le plus. Suffisant pour un MVP sans NLP.
    meilleur = (None, 0)
    for categorie, mots in MOTS_CLES_CATEGORIES.items():
        score = sum(1 for mot in mots if mot in texte)
        if score > meilleur[1]:
            meilleur = (categorie, score)
    return meilleur


def _options_categories(avec_suggestion=False):
    """Construit la liste des 4 catégories à proposer à l'étudiant.

    Si `avec_suggestion=True`, ajoute une option 'suggerer' pour
    laisser le bot proposer une catégorie d'après la description.
    """
    options = [
        {'value': value, 'label': label}
        for value, label in Reclamation.CATEGORIE_CHOICES
    ]
    if avec_suggestion:
        # Bonus S3.2 : permet à l'étudiant indécis de décrire son
        # problème et de laisser le bot deviner la catégorie.
        options.append({'value': 'suggerer', 'label': 'Pas sûr, suggérez-moi'})
    return options


def _categorie_label(conversation):
    # Renvoie le libellé humain ("Notes", "Bourse"...) de la catégorie
    # mémorisée dans le contexte, ou '' si aucune.
    return dict(Reclamation.CATEGORIE_CHOICES).get(
        conversation.contexte.get('categorie'), ''
    )


def _creer_reclamation(conversation):
    """Persiste la réclamation à partir du contexte de la conversation.

    La description enregistrée inclut les précisions obtenues lors de
    l'étape DETAILS_DEMANDES. La référence finale (REC-AAAA-NNN) est
    attribuée automatiquement par Reclamation.save() — cf. S2.4.
    """
    reclamation = Reclamation.objects.create(
        etudiant=conversation.etudiant,
        categorie=conversation.contexte['categorie'],
        description=_formatter_description_complete(conversation),
        statut=Reclamation.STATUT_SOUMISE,
    )
    # On garde les références dans le contexte pour pouvoir afficher la
    # référence dans le message final ET retrouver la réclamation depuis
    # l'historique des conversations.
    conversation.contexte['reclamation_id'] = reclamation.pk
    conversation.contexte['reference'] = reclamation.reference
    return reclamation


# ---------------------------------------------------------------------------
# Calcul de la réponse du bot pour un état donné.
# Cette fonction est PURE : elle n'écrit rien en base.
# ---------------------------------------------------------------------------

def reponse_pour(conversation):
    """Calcule la réponse du bot pour l'état courant de la conversation."""
    etat = conversation.etat

    if etat == Conversation.ETAT_ACCUEIL:
        # Message d'accueil personnalisé avec le prénom de l'étudiant.
        return {
            'message': (
                f"Bonjour {conversation.etudiant.first_name or conversation.etudiant.username} ! "
                "Je suis le chatbot des réclamations académiques. "
                'Que souhaitez-vous faire ?'
            ),
            'options': [
                {'value': 'deposer', 'label': 'Déposer une réclamation'},
                {'value': 'suivre', 'label': 'Suivre une réclamation'},
            ],
        }

    if etat == Conversation.ETAT_CATEGORIE_DEMANDEE:
        return {
            'message': 'Dans quelle catégorie se situe votre réclamation ?',
            'options': _options_categories(avec_suggestion=True),
        }

    if etat == Conversation.ETAT_DESCRIPTION_POUR_SUGGESTION:
        # Branche déclenchée quand l'étudiant a cliqué sur "suggerer".
        return {
            'message': (
                'Pas de souci, décrivez votre problème et je vous suggérerai '
                'une catégorie adaptée.'
            ),
            'options': [],
        }

    if etat == Conversation.ETAT_SUGGESTION_PROPOSEE:
        suggestion = conversation.contexte.get('categorie_suggeree')
        label = dict(Reclamation.CATEGORIE_CHOICES).get(suggestion, '')
        if suggestion:
            # Cas nominal : on a trouvé une catégorie probable.
            return {
                'message': (
                    f"D'après votre description, la catégorie la plus probable est : "
                    f"« {label} ». Souhaitez-vous l'accepter ou choisir une autre catégorie ?"
                ),
                'options': [
                    {'value': 'accepter', 'label': f'Accepter ({label})'},
                    {'value': 'modifier', 'label': 'Choisir une autre catégorie'},
                ],
            }
        # Cas dégradé : aucun mot-clé reconnu → on demande un choix manuel.
        return {
            'message': (
                "Je n'ai pas pu deviner la catégorie automatiquement. "
                'Pouvez-vous la sélectionner manuellement ?'
            ),
            'options': _options_categories(),
        }

    if etat == Conversation.ETAT_DESCRIPTION_DEMANDEE:
        return {
            'message': (
                f"Catégorie sélectionnée : {_categorie_label(conversation)}. "
                'Pouvez-vous décrire votre problème ?'
            ),
            'options': [],
        }

    if etat == Conversation.ETAT_DETAILS_DEMANDES:
        question = _question_courante(conversation)
        if question is None:
            # Plus de question : on devrait être passé à RECAPITULATIF.
            # Ce return est un garde-fou si le contexte est incohérent.
            return {'message': 'Merci pour ces précisions.', 'options': []}
        # Indicateur de progression "Précision 2/3" pour rassurer l'étudiant.
        total = len(_questions_pour(conversation.contexte.get('categorie')))
        idx = conversation.contexte.get('details_index', 0) + 1
        return {
            'message': (
                f"Précision {idx}/{total} — {question['question']}\n"
                f"({question['exemple']})"
            ),
            'options': [],
        }

    if etat == Conversation.ETAT_RECAPITULATIF:
        # Récapitulatif complet avant validation : l'étudiant relit tout
        # ce qu'il a saisi avant de cliquer sur "Confirmer".
        details = conversation.contexte.get('details', {})
        questions = _questions_pour(conversation.contexte.get('categorie'))
        lignes_details = ''
        if details:
            lignes_details = '\nPrécisions :\n' + '\n'.join(
                f"  • {q['question']} → {details.get(q['key'], '(passé)')}" for q in questions
            )
        return {
            'message': (
                'Voici le récapitulatif de votre réclamation :\n'
                f"• Catégorie : {_categorie_label(conversation)}\n"
                f"• Description : {conversation.contexte.get('description', '')}"
                f"{lignes_details}\n\n"
                'Confirmez-vous le dépôt ?'
            ),
            'options': [
                {'value': 'confirmer', 'label': 'Confirmer'},
                {'value': 'annuler', 'label': 'Annuler'},
            ],
        }

    if etat == Conversation.ETAT_SUIVI_REF_DEMANDEE:
        # Détaillé en S3.1 — flux "suivre une réclamation existante".
        return {
            'message': 'Veuillez saisir la référence de votre réclamation (ex. REC-2026-001).',
            'options': [],
        }

    if etat == Conversation.ETAT_TERMINEE:
        reference = conversation.contexte.get('reference')
        if reference:
            # Cas confirmation de dépôt : on met en avant la référence
            # que l'étudiant devra réutiliser pour le suivi.
            return {
                'message': (
                    'Votre réclamation a bien été enregistrée avec le statut « Soumise ».\n'
                    f"Votre référence de suivi : {reference}\n"
                    "Conservez-la pour consulter l'avancement de votre dossier. À bientôt !"
                ),
                'options': [],
                'reference': reference,
            }
        # Cas annulation ou flux suivi sans création.
        return {'message': 'Conversation terminée. À bientôt !', 'options': []}

    # Fallback défensif : si un état non géré apparaît (ex: nouvel état
    # ajouté sans mise à jour de cette fonction), on renvoie un message
    # neutre plutôt que de crasher.
    return {'message': '...', 'options': []}


# ---------------------------------------------------------------------------
# Machine à états : transitions selon l'action ou le texte reçu.
# Chaque branche valide l'entrée, met à jour le contexte, sauvegarde
# en base, puis délègue à reponse_pour() pour calculer la réponse.
# ---------------------------------------------------------------------------

def traiter_message(conversation, action='', texte=''):
    """Fait avancer la conversation selon l'action ou le texte reçu.

    Renvoie la nouvelle réponse du bot après transition.
    """
    etat = conversation.etat

    # --- ACCUEIL : choix entre "déposer" et "suivre". ---
    if etat == Conversation.ETAT_ACCUEIL:
        if action == 'deposer':
            conversation.etat = Conversation.ETAT_CATEGORIE_DEMANDEE
        elif action == 'suivre':
            conversation.etat = Conversation.ETAT_SUIVI_REF_DEMANDEE
        else:
            # Entrée invalide : on reste sur place et on rappelle les
            # options à choisir.
            return {
                'message': 'Merci de choisir une option : déposer ou suivre une réclamation.',
                'options': reponse_pour(conversation)['options'],
            }
        conversation.save(update_fields=['etat', 'date_maj'])
        return reponse_pour(conversation)

    # --- CATEGORIE_DEMANDEE : 4 catégories ou "suggérer". ---
    if etat == Conversation.ETAT_CATEGORIE_DEMANDEE:
        if action == 'suggerer':
            # Bascule sur la branche "suggestion automatique".
            conversation.etat = Conversation.ETAT_DESCRIPTION_POUR_SUGGESTION
            conversation.save(update_fields=['etat', 'date_maj'])
            return reponse_pour(conversation)
        # Validation stricte : on n'accepte que les valeurs définies dans
        # le modèle, pas n'importe quel texte envoyé par le client.
        categories_valides = {value for value, _ in Reclamation.CATEGORIE_CHOICES}
        if action not in categories_valides:
            return {
                'message': 'Merci de choisir une catégorie parmi celles proposées.',
                'options': _options_categories(avec_suggestion=True),
            }
        conversation.contexte['categorie'] = action
        conversation.etat = Conversation.ETAT_DESCRIPTION_DEMANDEE
        conversation.save(update_fields=['etat', 'contexte', 'date_maj'])
        return reponse_pour(conversation)

    # --- DESCRIPTION_POUR_SUGGESTION : on lit la description et on devine. ---
    if etat == Conversation.ETAT_DESCRIPTION_POUR_SUGGESTION:
        description = (texte or '').strip()
        # Validation minimale : on ne devine pas sur 3 caractères.
        if len(description) < 5:
            return {
                'message': "Merci de décrire votre problème en quelques mots (au moins 5 caractères).",
                'options': [],
            }
        suggestion, _score = suggerer_categorie(description)
        # On mémorise la description et la suggestion ; la décision finale
        # appartient à l'étudiant à l'état suivant.
        conversation.contexte['description'] = description
        conversation.contexte['categorie_suggeree'] = suggestion
        conversation.etat = Conversation.ETAT_SUGGESTION_PROPOSEE
        conversation.save(update_fields=['etat', 'contexte', 'date_maj'])
        return reponse_pour(conversation)

    # --- SUGGESTION_PROPOSEE : accepter, modifier, ou choisir directement. ---
    if etat == Conversation.ETAT_SUGGESTION_PROPOSEE:
        suggestion = conversation.contexte.get('categorie_suggeree')
        if action == 'accepter' and suggestion:
            # L'étudiant valide la suggestion : on initialise les détails
            # et on enchaîne sur les questions complémentaires (si la
            # catégorie en a) ou directement sur le récap.
            conversation.contexte['categorie'] = suggestion
            conversation.contexte.setdefault('details', {})
            conversation.contexte['details_index'] = 0
            if _questions_pour(suggestion):
                conversation.etat = Conversation.ETAT_DETAILS_DEMANDES
            else:
                conversation.etat = Conversation.ETAT_RECAPITULATIF
            conversation.save(update_fields=['etat', 'contexte', 'date_maj'])
            return reponse_pour(conversation)
        if action == 'modifier' or not suggestion:
            # Pas de suggestion utilisable, ou refus → on retourne sur le
            # choix manuel des catégories (sans option "suggérer" cette fois).
            conversation.etat = Conversation.ETAT_CATEGORIE_DEMANDEE
            conversation.save(update_fields=['etat', 'date_maj'])
            return {
                'message': 'Choisissez la catégorie qui vous semble la plus adaptée.',
                'options': _options_categories(),
            }
        # Raccourci : l'étudiant peut aussi cliquer directement sur l'une
        # des 4 catégories proposées dans la liste de fallback.
        categories_valides = {value for value, _ in Reclamation.CATEGORIE_CHOICES}
        if action in categories_valides:
            conversation.contexte['categorie'] = action
            conversation.contexte.setdefault('details', {})
            conversation.contexte['details_index'] = 0
            if _questions_pour(action):
                conversation.etat = Conversation.ETAT_DETAILS_DEMANDES
            else:
                conversation.etat = Conversation.ETAT_RECAPITULATIF
            conversation.save(update_fields=['etat', 'contexte', 'date_maj'])
            return reponse_pour(conversation)
        # Action inconnue : on re-pose la question.
        return reponse_pour(conversation)

    # --- DESCRIPTION_DEMANDEE : description après choix manuel. ---
    if etat == Conversation.ETAT_DESCRIPTION_DEMANDEE:
        description = (texte or '').strip()
        if len(description) < 5:
            return {
                'message': "Merci de décrire votre problème en quelques mots (au moins 5 caractères).",
                'options': [],
            }
        conversation.contexte['description'] = description
        conversation.contexte.setdefault('details', {})
        conversation.contexte['details_index'] = 0
        # Si la catégorie a des questions complémentaires, on les pose.
        # Sinon (catégorie sans questions définies), on va direct au récap.
        if _questions_pour(conversation.contexte.get('categorie')):
            conversation.etat = Conversation.ETAT_DETAILS_DEMANDES
        else:
            conversation.etat = Conversation.ETAT_RECAPITULATIF
        conversation.save(update_fields=['etat', 'contexte', 'date_maj'])
        return reponse_pour(conversation)

    # --- DETAILS_DEMANDES : boucle sur les questions complémentaires. ---
    if etat == Conversation.ETAT_DETAILS_DEMANDES:
        question = _question_courante(conversation)
        if question is None:
            # Sécurité : si on entre ici sans question, on saute au récap.
            conversation.etat = Conversation.ETAT_RECAPITULATIF
            conversation.save(update_fields=['etat', 'date_maj'])
            return reponse_pour(conversation)
        reponse = (texte or '').strip()
        if len(reponse) < 2:
            return {
                'message': (
                    "Cette précision est nécessaire pour traiter votre réclamation. "
                    "Merci de répondre (au moins 2 caractères)."
                ),
                'options': [],
            }
        # Enregistrement de la réponse + passage à la question suivante.
        conversation.contexte.setdefault('details', {})[question['key']] = reponse
        conversation.contexte['details_index'] = conversation.contexte.get('details_index', 0) + 1
        # Si plus de question : récap
        if _question_courante(conversation) is None:
            conversation.etat = Conversation.ETAT_RECAPITULATIF
        conversation.save(update_fields=['etat', 'contexte', 'date_maj'])
        return reponse_pour(conversation)

    # --- RECAPITULATIF : confirmation finale. ---
    if etat == Conversation.ETAT_RECAPITULATIF:
        if action == 'confirmer':
            # C'est ici qu'on persiste réellement la réclamation en base.
            _creer_reclamation(conversation)
            conversation.etat = Conversation.ETAT_TERMINEE
            conversation.save(update_fields=['etat', 'contexte', 'date_maj'])
            return reponse_pour(conversation)
        if action == 'annuler':
            # Aucune réclamation créée : on termine la conversation
            # sans toucher à la table reclamations.
            conversation.etat = Conversation.ETAT_TERMINEE
            conversation.save(update_fields=['etat', 'date_maj'])
            return {
                'message': 'Dépôt annulé. Aucune réclamation n’a été enregistrée.',
                'options': [],
            }
        return {
            'message': 'Veuillez confirmer ou annuler.',
            'options': reponse_pour(conversation)['options'],
        }

    # --- SUIVI_REF_DEMANDEE : recherche d'une réclamation par référence. ---
    if etat == Conversation.ETAT_SUIVI_REF_DEMANDEE:
        # Normalisation : .upper() pour accepter "rec-2026-001" comme
        # "REC-2026-001".
        reference = (texte or '').strip().upper()
        if not reference:
            return {
                'message': 'Merci de saisir une référence (ex. REC-2026-001).',
                'options': [],
            }
        # Filtre etudiant=... : un étudiant ne peut suivre QUE ses propres
        # réclamations, jamais celle d'un autre même en connaissant la réf.
        reclamation = Reclamation.objects.filter(
            reference=reference,
            etudiant=conversation.etudiant,
        ).first()
        if reclamation is None:
            return {
                'message': (
                    f"Aucune réclamation trouvée pour la référence « {reference} ». "
                    'Vérifiez la référence et réessayez.'
                ),
                'options': [],
            }
        # On mémorise les infos puis on affiche l'état courant.
        conversation.contexte['reference'] = reclamation.reference
        conversation.contexte['reclamation_id'] = reclamation.pk
        conversation.etat = Conversation.ETAT_TERMINEE
        conversation.save(update_fields=['etat', 'contexte', 'date_maj'])
        return {
            'message': (
                f"Voici l'état de votre réclamation {reclamation.reference} :\n"
                f"• Catégorie : {reclamation.get_categorie_display()}\n"
                f"• Statut : {reclamation.get_statut_display()}\n"
                f"• Dernière mise à jour : {reclamation.date_maj:%d/%m/%Y à %H:%M}"
            ),
            'options': [],
            # Données structurées renvoyées en plus du message pour que le
            # frontend puisse les afficher dans une carte dédiée si besoin.
            'reclamation': {
                'reference': reclamation.reference,
                'categorie': reclamation.categorie,
                'statut': reclamation.statut,
                'date_maj': reclamation.date_maj.isoformat(),
            },
        }

    # Fallback : état non géré → on renvoie la réponse courante sans
    # transition (la conversation est probablement déjà TERMINEE).
    return reponse_pour(conversation)
