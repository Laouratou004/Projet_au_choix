"""Moteur de dialogue du chatbot.

Le chatbot est une machine à états. Chaque état correspond à une étape
du parcours guidé. `reponse_pour(conversation)` calcule la réponse à
renvoyer en fonction de l'état courant ; `traiter_message(conversation,
action, texte)` fait avancer la conversation vers l'état suivant.
"""
from .models import Conversation


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
        # Détaillé en S2.2.
        return {
            'message': 'Parcours de dépôt lancé. Quelle est la catégorie de votre réclamation ?',
            'options': [],
        }

    if etat == Conversation.ETAT_SUIVI_REF_DEMANDEE:
        # Détaillé en S3.1.
        return {
            'message': 'Veuillez saisir la référence de votre réclamation (ex. REC-2026-001).',
            'options': [],
        }

    if etat == Conversation.ETAT_TERMINEE:
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
