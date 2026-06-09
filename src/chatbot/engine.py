"""Moteur de dialogue du chatbot.

Le chatbot est une machine à états. Chaque état correspond à une étape
du parcours guidé. `reponse_pour(conversation)` calcule la réponse à
renvoyer en fonction de l'état courant ; `traiter_message(conversation,
action, texte)` fait avancer la conversation vers l'état suivant.
"""
import uuid

from reclamations.models import Reclamation

from .models import Conversation


def _options_categories():
    """Construit la liste des 4 catégories à proposer à l'étudiant."""
    return [
        {'value': value, 'label': label}
        for value, label in Reclamation.CATEGORIE_CHOICES
    ]


def _categorie_label(conversation):
    return dict(Reclamation.CATEGORIE_CHOICES).get(
        conversation.contexte.get('categorie'), ''
    )


def _generer_reference_temporaire():
    """Référence unique posée à la création (le format final REC-AAAA-NNN
    sera attribué en S2.4)."""
    return f"TMP-{uuid.uuid4().hex[:10].upper()}"


def _creer_reclamation(conversation):
    """Persiste la réclamation à partir du contexte de la conversation."""
    reclamation = Reclamation.objects.create(
        etudiant=conversation.etudiant,
        categorie=conversation.contexte['categorie'],
        description=conversation.contexte['description'],
        statut=Reclamation.STATUT_SOUMISE,
        reference=_generer_reference_temporaire(),
    )
    conversation.contexte['reclamation_id'] = reclamation.pk
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

    if etat == Conversation.ETAT_RECAPITULATIF:
        return {
            'message': (
                'Voici le récapitulatif de votre réclamation :\n'
                f"• Catégorie : {_categorie_label(conversation)}\n"
                f"• Description : {conversation.contexte.get('description', '')}\n\n"
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
        reclamation_id = conversation.contexte.get('reclamation_id')
        if reclamation_id:
            return {
                'message': (
                    'Votre réclamation a bien été enregistrée avec le statut « Soumise ». '
                    "L'administration la prendra en charge prochainement. À bientôt !"
                ),
                'options': [],
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
        categories_valides = {value for value, _ in Reclamation.CATEGORIE_CHOICES}
        if action not in categories_valides:
            return {
                'message': 'Merci de choisir une catégorie parmi celles proposées.',
                'options': _options_categories(),
            }
        conversation.contexte['categorie'] = action
        conversation.etat = Conversation.ETAT_DESCRIPTION_DEMANDEE
        conversation.save(update_fields=['etat', 'contexte', 'date_maj'])
        return reponse_pour(conversation)

    if etat == Conversation.ETAT_DESCRIPTION_DEMANDEE:
        description = (texte or '').strip()
        if len(description) < 5:
            return {
                'message': "Merci de décrire votre problème en quelques mots (au moins 5 caractères).",
                'options': [],
            }
        conversation.contexte['description'] = description
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

    return reponse_pour(conversation)
