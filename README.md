# 💊 Medicine Cabinet — Suivi d'armoire à pharmacie pour Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/thom69170/home-medicine-cabinet-tracking/actions/workflows/validate.yml/badge.svg)](https://github.com/thom69170/home-medicine-cabinet-tracking/actions/workflows/validate.yml)

Intégration personnalisée pour **Home Assistant**, installable via **HACS**, qui permet de suivre le contenu de votre (ou vos) armoire(s) à pharmacie :

- 📦 **Quantité** en stock, avec unité libre (comprimés, ml, boîtes, sachets...)
- 📅 **Date de péremption**, avec calcul automatique du nombre de jours restants
- 🩺 **Utilité** du médicament (fièvre, douleur, allergie, etc.) et catégorie libre
- ⚠️ Détection automatique des médicaments **périmés**, **bientôt périmés** ou en **stock bas**
- 🗓️ Un **calendrier** listant toutes les dates de péremption
- 🎴 Une **carte de tableau de bord** façon *Grocy* : grille de médicaments avec badges colorés (périmé / bientôt périmé / stock bas), boutons +/- rapides, recherche — installée automatiquement, sans configuration
- 🔧 Des **services** pour ajouter, mettre à jour, supprimer, consommer ou réapprovisionner un médicament — directement utilisables dans vos automatisations, scripts ou tableaux de bord

## Installation

### Via HACS (recommandé)

1. Ouvrez HACS dans Home Assistant.
2. Menu **⋮** → **Dépôts personnalisés**.
3. Ajoutez l'URL de ce dépôt avec la catégorie **Intégration**.
4. Recherchez **Medicine Cabinet** dans HACS et installez-le.
5. Redémarrez Home Assistant.

### Installation manuelle

Copiez le dossier `custom_components/medicine_cabinet` dans le répertoire `config/custom_components/` de votre installation Home Assistant, puis redémarrez.

## Configuration

1. **Paramètres** → **Appareils et services** → **Ajouter une intégration**.
2. Recherchez **Medicine Cabinet**.
3. Donnez un nom à votre armoire (ex. *Armoire salle de bain*). Vous pouvez créer plusieurs armoires (une par pièce, par personne...).
4. Dans les options de l'intégration, réglez :
   - le nombre de jours avant péremption à partir duquel un médicament est considéré « bientôt périmé » (30 par défaut) ;
   - le seuil de stock bas par défaut, utilisé quand un médicament n'a pas de seuil personnalisé.

## Entités créées

Pour chaque armoire configurée :

| Entité | Description |
|---|---|
| `sensor.<nom>_total_medicaments` | Nombre total de médicaments suivis |
| `sensor.<nom>_medicaments_perimes` | Nombre de médicaments périmés (liste en attribut) |
| `sensor.<nom>_medicaments_bientot_perimes` | Nombre de médicaments bientôt périmés |
| `sensor.<nom>_medicaments_en_stock_bas` | Nombre de médicaments en stock bas |
| `calendar.<nom>_peremptions` | Calendrier des dates de péremption |
| `sensor.<nom_du_medicament>` | Un capteur par médicament, état = quantité, avec en attributs : date de péremption, utilité, catégorie, emplacement, notes, jours restants, périmé/bientôt périmé/stock bas |

## Ajouter un médicament

Le plus simple est d'utiliser le service `medicine_cabinet.add_medication`, par exemple via **Outils de développement → Actions** :

```yaml
action: medicine_cabinet.add_medication
data:
  config_entry_id: <sélectionnez votre armoire>
  name: "Doliprane 500mg"
  quantity: 16
  unit: "comprimés"
  expiration_date: "2027-03-01"
  purpose: "Fièvre et douleur"
  category: "Antidouleur"
  minimum_quantity: 8
  location: "Armoire salle de bain"
```

L'identifiant du médicament (nécessaire pour `update_medication`, `remove_medication`, `consume` et `restock`) est visible dans l'attribut `id` du capteur créé, ou en écoutant la réponse du service.

## Services disponibles

| Service | Description |
|---|---|
| `medicine_cabinet.add_medication` | Ajoute un médicament |
| `medicine_cabinet.update_medication` | Met à jour un médicament existant |
| `medicine_cabinet.remove_medication` | Supprime un médicament |
| `medicine_cabinet.consume` | Diminue la quantité (prise du médicament) |
| `medicine_cabinet.restock` | Augmente la quantité (réapprovisionnement) |

Tous les champs et exemples sont documentés directement dans l'interface **Outils de développement → Actions** de Home Assistant.

## Automatisation d'exemple : alerte de péremption

```yaml
automation:
  - alias: "Pharmacie - alerte péremption proche"
    trigger:
      - platform: state
        entity_id: sensor.armoire_salle_de_bain_medicaments_bientot_perimes
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state | int > 0 }}"
    action:
      - service: notify.mobile_app_mon_telephone
        data:
          title: "Médicaments bientôt périmés"
          message: >
            {{ state_attr('sensor.armoire_salle_de_bain_medicaments_bientot_perimes', 'medications') | join(', ') }}
```

Vous pouvez aussi réagir aux événements `medicine_cabinet_expired`, `medicine_cabinet_expiring_soon` et `medicine_cabinet_low_stock`, déclenchés dès qu'un médicament change d'état.

## Carte de tableau de bord (façon Grocy)

L'intégration embarque sa propre carte Lovelace, **`medicine-cabinet-card`**, installée et chargée automatiquement (aucune ressource à ajouter à la main). Elle affiche vos médicaments sous forme de grille de cartes colorées — nom, catégorie, utilité, quantité avec boutons +/- rapides, date de péremption et statut (OK / bientôt périmé / périmé / stock bas) — avec un champ de recherche, dans le même esprit que la vue « produits » de Grocy.

Ajoutez-la simplement dans l'éditeur de tableau de bord (mode YAML) :

```yaml
type: custom:medicine-cabinet-card
title: "Armoire salle de bain"
```

Options facultatives :

| Option | Description |
|---|---|
| `title` | Titre affiché en haut de la carte. |
| `device_id` | Limite l'affichage à une seule armoire (utile si vous en avez plusieurs) — identifiant visible dans l'URL de la page de l'appareil. |
| `entities` | Liste explicite d'entités à afficher, si vous préférez composer la sélection vous-même. |

Sans `device_id` ni `entities`, la carte détecte et affiche automatiquement tous les médicaments de toutes vos armoires.

## Exemple de tableau de bord (cartes standard)

```yaml
type: entities
title: Armoire à pharmacie
entities:
  - entity: sensor.armoire_salle_de_bain_total_medicaments
  - entity: sensor.armoire_salle_de_bain_medicaments_perimes
  - entity: sensor.armoire_salle_de_bain_medicaments_bientot_perimes
  - entity: sensor.armoire_salle_de_bain_medicaments_en_stock_bas
  - entity: calendar.armoire_salle_de_bain_peremptions
```

Pour afficher automatiquement tous les capteurs de médicaments avec les cartes standard (sans les lister un par un), la carte [auto-entities](https://github.com/thomasloven/lovelace-auto-entities) (installable via HACS) fonctionne bien, en filtrant par appareil sur l'armoire concernée.

## Licence

MIT — voir [LICENSE](LICENSE).
