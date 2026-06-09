"""Moteur de dialogue du chatbot.

Le chatbot est une machine à états. Chaque état correspond à une étape
du parcours guidé. `reponse_pour(conversation)` calcule la réponse à
renvoyer en fonction de l'état courant ; `traiter_message(conversation,
action, texte)` fait avancer la conversation vers l'état suivant.
"""
from reclamations.models import Reclamation

from .models import Conversation


def _options_categories():
    """Construit la liste des 4 catégories à proposer à l'étudiant."""
    return [
        {'value': value, 'label': label}
        for value, label in Reclamation.CATEGORIE_CHOICES
    ]


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
        # Détaillé en S2.3.
        categorie_label = dict(Reclamation.CATEGORIE_CHOICES).get(
            conversation.contexte.get('categorie'), ''
        )
        return {
            'message': (
                f"Catégorie sélectionnée : {categorie_label}. "
                'Pouvez-vous décrire votre problème ?'
            ),
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

    return reponse_pour(conversation)
