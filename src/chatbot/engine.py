"""Moteur de dialogue du chatbot.

Le chatbot est une machine à états. Chaque état correspond à une étape
du parcours guidé. `reponse_pour(conversation)` calcule la réponse à
renvoyer en fonction de l'état courant ; `traiter_message(conversation,
action, texte)` fait avancer la conversation vers l'état suivant.
"""
import unicodedata

from reclamations.models import Reclamation

from .models import Conversation


# Mots-clés par catégorie (en minuscules, sans accents). Sert à la
# suggestion automatique en S3.2 — bonus.
# Questions complémentaires à poser après la description initiale.
# Chaque question est un dict { key, question, exemple }. Les réponses sont
# stockées dans Conversation.contexte['details'][key] puis concaténées à
# la description finale de la Réclamation pour donner du contexte à l'admin.
QUESTIONS_DETAILS = {
    'notes': [
        {'key': 'matiere',     'question': 'Quelle est la matière ou le cours concerné ?',           'exemple': 'ex. Algèbre linéaire'},
        {'key': 'semestre',    'question': 'À quel semestre / année universitaire cela se rapporte-t-il ?', 'exemple': 'ex. Semestre 2, 2025-2026'},
        {'key': 'enseignant',  'question': "Quel est le nom de l'enseignant (si vous le connaissez) ?", 'exemple': 'ex. M. Diallo (optionnel, tapez "ras")'},
    ],
    'scolarite': [
        {'key': 'document',    'question': 'De quel document ou démarche s’agit-il exactement ?',    'exemple': 'ex. certificat de scolarité, attestation, carte étudiant'},
        {'key': 'depuis_quand','question': 'Depuis quand attendez-vous une réponse ou la délivrance ?', 'exemple': 'ex. depuis 3 semaines'},
    ],
    'examens': [
        {'key': 'examen',      'question': 'De quel examen s’agit-il ?',                              'exemple': 'ex. Examen final de Bases de données'},
        {'key': 'date_examen', 'question': 'À quelle date est-il prévu (ou a-t-il eu lieu) ?',         'exemple': 'ex. 12/06/2026'},
        {'key': 'justificatif','question': 'Avez-vous un justificatif à fournir ?',                   'exemple': 'ex. certificat médical / non'},
    ],
    'bourse': [
        {'key': 'periode',     'question': 'Quelle période ou mois est concerné ?',                   'exemple': 'ex. Avril 2026'},
        {'key': 'montant',     'question': 'Quel montant est attendu (si vous le savez) ?',           'exemple': 'ex. 350 000 GNF (optionnel, tapez "ras")'},
        {'key': 'dossier',     'question': 'Avez-vous un numéro de dossier ou de contrat de bourse ?', 'exemple': 'ex. B-2025-1234 (optionnel)'},
    ],
}


def _questions_pour(categorie):
    return QUESTIONS_DETAILS.get(categorie, [])


def _question_courante(conversation):
    """Renvoie la question en cours (selon details_index) ou None si terminé."""
    questions = _questions_pour(conversation.contexte.get('categorie'))
    idx = conversation.contexte.get('details_index', 0)
    if 0 <= idx < len(questions):
        return questions[idx]
    return None


def _formatter_description_complete(conversation):
    """Description initiale + détails formatés pour l'admin."""
    desc = conversation.contexte.get('description', '')
    details = conversation.contexte.get('details', {})
    questions = _questions_pour(conversation.contexte.get('categorie'))
    if not details:
        return desc
    lignes = [desc.strip(), '', '--- Précisions ---']
    for q in questions:
        rep = details.get(q['key'])
        if rep:
            lignes.append(f"• {q['question']} → {rep}")
    return '\n'.join(lignes)


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
    sans_accent = unicodedata.normalize('NFD', texte)
    sans_accent = ''.join(c for c in sans_accent if unicodedata.category(c) != 'Mn')
    return sans_accent.lower()


def suggerer_categorie(description):
    """Devine la catégorie la plus probable à partir de la description.

    Renvoie un tuple (categorie, nombre_de_matches). Si aucun mot-clé
    n'est trouvé, renvoie (None, 0).
    """
    texte = _normaliser(description)
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
        options.append({'value': 'suggerer', 'label': 'Pas sûr, suggérez-moi'})
    return options


def _categorie_label(conversation):
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
    conversation.contexte['reclamation_id'] = reclamation.pk
    conversation.contexte['reference'] = reclamation.reference
    return reclamation


def reponse_pour(conversation):
    """Calcule la réponse du bot pour l'état courant de la conversation."""
    etat = conversation.etat

    if etat == Conversation.ETAT_ACCUEIL:
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
            return {'message': 'Merci pour ces précisions.', 'options': []}
        total = len(_questions_pour(conversation.contexte.get('categorie')))
        idx = conversation.contexte.get('details_index', 0) + 1
        return {
            'message': (
                f"Précision {idx}/{total} — {question['question']}\n"
                f"({question['exemple']})"
            ),
            'options': [
                {'value': 'passer', 'label': 'Passer cette question'},
            ],
        }

    if etat == Conversation.ETAT_RECAPITULATIF:
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
        # Détaillé en S3.1.
        return {
            'message': 'Veuillez saisir la référence de votre réclamation (ex. REC-2026-001).',
            'options': [],
        }

    if etat == Conversation.ETAT_TERMINEE:
        reference = conversation.contexte.get('reference')
        if reference:
            return {
                'message': (
                    'Votre réclamation a bien été enregistrée avec le statut « Soumise ».\n'
                    f"Votre référence de suivi : {reference}\n"
                    "Conservez-la pour consulter l'avancement de votre dossier. À bientôt !"
                ),
                'options': [],
                'reference': reference,
            }
        return {'message': 'Conversation terminée. À bientôt !', 'options': []}

    return {'message': '...', 'options': []}


def traiter_message(conversation, action='', texte=''):
    """Fait avancer la conversation selon l'action ou le texte reçu.

    Renvoie la nouvelle réponse du bot après transition.
    """
    etat = conversation.etat

    if etat == Conversation.ETAT_ACCUEIL:
        if action == 'deposer':
            conversation.etat = Conversation.ETAT_CATEGORIE_DEMANDEE
        elif action == 'suivre':
            conversation.etat = Conversation.ETAT_SUIVI_REF_DEMANDEE
        else:
            return {
                'message': 'Merci de choisir une option : déposer ou suivre une réclamation.',
                'options': reponse_pour(conversation)['options'],
            }
        conversation.save(update_fields=['etat', 'date_maj'])
        return reponse_pour(conversation)

    if etat == Conversation.ETAT_CATEGORIE_DEMANDEE:
        if action == 'suggerer':
            conversation.etat = Conversation.ETAT_DESCRIPTION_POUR_SUGGESTION
            conversation.save(update_fields=['etat', 'date_maj'])
            return reponse_pour(conversation)
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

    if etat == Conversation.ETAT_DESCRIPTION_POUR_SUGGESTION:
        description = (texte or '').strip()
        if len(description) < 5:
            return {
                'message': "Merci de décrire votre problème en quelques mots (au moins 5 caractères).",
                'options': [],
            }
        suggestion, _score = suggerer_categorie(description)
        conversation.contexte['description'] = description
        conversation.contexte['categorie_suggeree'] = suggestion
        conversation.etat = Conversation.ETAT_SUGGESTION_PROPOSEE
        conversation.save(update_fields=['etat', 'contexte', 'date_maj'])
        return reponse_pour(conversation)

    if etat == Conversation.ETAT_SUGGESTION_PROPOSEE:
        suggestion = conversation.contexte.get('categorie_suggeree')
        if action == 'accepter' and suggestion:
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
            conversation.etat = Conversation.ETAT_CATEGORIE_DEMANDEE
            conversation.save(update_fields=['etat', 'date_maj'])
            return {
                'message': 'Choisissez la catégorie qui vous semble la plus adaptée.',
                'options': _options_categories(),
            }
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
        return reponse_pour(conversation)

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

    if etat == Conversation.ETAT_DETAILS_DEMANDES:
        question = _question_courante(conversation)
        if question is None:
            conversation.etat = Conversation.ETAT_RECAPITULATIF
            conversation.save(update_fields=['etat', 'date_maj'])
            return reponse_pour(conversation)
        if action == 'passer':
            reponse = '(passé)'
        else:
            reponse = (texte or '').strip()
            if not reponse:
                return {
                    'message': "Merci de répondre, ou cliquez sur « Passer cette question ».",
                    'options': [{'value': 'passer', 'label': 'Passer cette question'}],
                }
        conversation.contexte.setdefault('details', {})[question['key']] = reponse
        conversation.contexte['details_index'] = conversation.contexte.get('details_index', 0) + 1
        # Si plus de question : récap
        if _question_courante(conversation) is None:
            conversation.etat = Conversation.ETAT_RECAPITULATIF
        conversation.save(update_fields=['etat', 'contexte', 'date_maj'])
        return reponse_pour(conversation)

    if etat == Conversation.ETAT_RECAPITULATIF:
        if action == 'confirmer':
            _creer_reclamation(conversation)
            conversation.etat = Conversation.ETAT_TERMINEE
            conversation.save(update_fields=['etat', 'contexte', 'date_maj'])
            return reponse_pour(conversation)
        if action == 'annuler':
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

    if etat == Conversation.ETAT_SUIVI_REF_DEMANDEE:
        reference = (texte or '').strip().upper()
        if not reference:
            return {
                'message': 'Merci de saisir une référence (ex. REC-2026-001).',
                'options': [],
            }
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
            'reclamation': {
                'reference': reclamation.reference,
                'categorie': reclamation.categorie,
                'statut': reclamation.statut,
                'date_maj': reclamation.date_maj.isoformat(),
            },
        }

    return reponse_pour(conversation)
