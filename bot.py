"""
Bot Discord Dofus

Fonctions actuelles :
- /defense
    Analyse une défense Perco/Prisme par OCR
    et enregistre le résultat dans Google Sheets.

- /main
    Permet à un joueur de déclarer une seule fois son Main Dofus.

- /setchanneldefense
    Permet à l'admin du bot ou à un modérateur Discord
    de définir le salon dans lequel /defense doit être utilisée.

- /showconfig
    Permet aux modérateurs de vérifier la configuration du serveur.


Variables nécessaires dans .env :

DISCORD_TOKEN=...
BOT_ADMIN_ID=...
SHEET_DEF_URL=...
SHEET_DATA_PLAYER=...

SHEET_DEF_URL :
    classeur contenant la feuille "combat"

SHEET_DATA_PLAYER :
    classeur "Données Joueurs" contenant l'onglet "Data_joueurs"


Fichiers locaux :
credentials.json
guild_config.json  -> généré automatiquement

guild_config.json doit être ajouté au .gitignore.
"""


# ============================================================
# IMPORTS
# ============================================================

import os
import json

import discord
import gspread

from dotenv import load_dotenv
from ocr import analyser_combat

from data_player import (
    charger_joueurs,
    trouver_main_par_id,
    trouver_id_par_main,
    attribuer_main,
    charger_players_nocta,
)

# ============================================================
# VARIABLES D'ENVIRONNEMENT
# ============================================================

load_dotenv()


token = os.getenv("DISCORD_TOKEN")


bot_admin_env = os.getenv("BOT_ADMIN_ID")

if bot_admin_env:
    bot_admin_id = int(bot_admin_env)
else:
    bot_admin_id = None


# URL du classeur PvP / défenses
sheet_def_url = (
    os.getenv("SHEET_DEF_URL")
    or os.getenv("GOOGLE_SHEET_URL")
)


# URL du classeur Données Joueurs
sheet_data_player_url = (
    os.getenv("SHEET_DATA_PLAYER")
    or os.getenv("GOOGLE_PLAYER_SHEET_URL")
)


if not token:
    raise RuntimeError(
        "DISCORD_TOKEN est absent du fichier .env"
    )


if not sheet_def_url:
    raise RuntimeError(
        "SHEET_DEF_URL est absent du fichier .env"
    )


if not sheet_data_player_url:
    raise RuntimeError(
        "SHEET_DATA_PLAYER est absent du fichier .env"
    )


# ============================================================
# GOOGLE SHEETS
# ============================================================

google_client = gspread.service_account(
    filename="credentials.json"
)


# Classeur utilisé par /defense
spreadsheet = google_client.open_by_url(
    sheet_def_url
)


# Classeur "Données Joueurs"
spreadsheet_base = google_client.open_by_url(
    sheet_data_player_url
)


# ============================================================
# CONFIGURATION LOCALE DU BOT
# ============================================================

CONFIG_FILE = "guild_config.json"


def load_guild_config():

    if not os.path.exists(CONFIG_FILE):
        return {}

    with open(
        CONFIG_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def save_guild_config(config):

    with open(
        CONFIG_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            config,
            file,
            indent=4,
            ensure_ascii=False
        )



# ============================================================
# DISCORD
# ============================================================

os.makedirs(
    "screenshots",
    exist_ok=True
)


# Nous utilisons uniquement des slash commands.
# message_content n'est donc plus nécessaire.
intents = discord.Intents.default()


client = discord.Client(
    intents=intents
)


tree = discord.app_commands.CommandTree(
    client
)


synced = False


# ============================================================
# OUTIL : VÉRIFIER SI UN UTILISATEUR PEUT CONFIGURER LE BOT
# ============================================================

def peut_configurer_bot(interaction):

    # Les commandes de configuration
    # ne doivent pas fonctionner en DM.
    if interaction.guild is None:
        return False


    # BOT_ADMIN_ID a toujours le droit.
    if (
        bot_admin_id is not None
        and interaction.user.id == bot_admin_id
    ):
        return True


    # Sinon on accepte aussi quelqu'un qui possède
    # la permission Discord "Gérer le serveur".
    return (
        interaction.user
        .guild_permissions
        .manage_guild
    )


# ============================================================
# EVENT : BOT CONNECTÉ
# ============================================================

@client.event
async def on_ready():

    global synced


    if not synced:

        await tree.sync()

        synced = True

        print(
            "Commandes slash synchronisées"
        )


    print(
        f"Bot connecté : {client.user}"
    )


# ============================================================
# COMMANDE : /setchanneldefense
# ============================================================

@tree.command(
    name="setchanneldefense",
    description="Définit le salon utilisé pour les défenses"
)
async def setchanneldefense(
    interaction: discord.Interaction
):

    if not peut_configurer_bot(interaction):

        await interaction.response.send_message(
            "Tu n'as pas la permission de modifier la configuration du bot.",
            ephemeral=True
        )

        return


    config = load_guild_config()


    # Les clés JSON sont enregistrées sous forme de texte.
    guild_id = str(
        interaction.guild_id
    )


    channel_id = (
        interaction.channel_id
    )


    # Si ce serveur n'existe pas encore
    # dans la configuration, on crée son dictionnaire.
    if guild_id not in config:

        config[guild_id] = {}


    # On mémorise le salon actuel.
    config[guild_id][
        "defense_channel_id"
    ] = channel_id


    save_guild_config(
        config
    )


    await interaction.response.send_message(
        (
            "Salon des défenses configuré : "
            f"<#{channel_id}>"
        ),
        ephemeral=True
    )


# ============================================================
# COMMANDE : /showconfig
# ============================================================

@tree.command(
    name="showconfig",
    description="Affiche la configuration du bot pour ce serveur"
)
async def showconfig(
    interaction: discord.Interaction
):

    if not peut_configurer_bot(interaction):

        await interaction.response.send_message(
            "Tu n'as pas la permission de voir cette configuration.",
            ephemeral=True
        )

        return


    config = load_guild_config()


    guild_id = str(
        interaction.guild_id
    )


    guild_config = config.get(
        guild_id,
        {}
    )


    defense_channel_id = (
        guild_config.get(
            "defense_channel_id"
        )
    )


    if defense_channel_id is None:

        texte = (
            "Aucun salon de défense "
            "n'est configuré."
        )

    else:

        texte = (
            "Salon des défenses : "
            f"<#{defense_channel_id}>"
        )


    await interaction.response.send_message(
        texte,
        ephemeral=True
    )


# ============================================================
# COMMANDE : /main
# ============================================================

@tree.command(
    name="main",
    description="Déclare ton pseudo principal Dofus"
)
async def main(
    interaction: discord.Interaction,
    pseudo: str
):

    resultat = attribuer_main(
    spreadsheet_base,
    interaction.user.id,
    pseudo
)


    if resultat == "OK":

        await interaction.response.send_message(
            (
                f'Ton Main "{pseudo.strip()}" '
                "a été enregistré."
            ),
            ephemeral=True
        )

        return


    if resultat == "Discord_ID_existant":

        main_actuel = trouver_main_par_id(
            charger_joueurs(spreadsheet_base),
            interaction.user.id
        )

        await interaction.response.send_message(
            (
                "Ton compte Discord possède "
                "déjà un Main enregistré : "
                f"**{main_actuel}**.\n"
                "Contacte un modérateur "
                "pour le modifier."
            ),
            ephemeral=True
        )

        return


    if resultat == "main_existant":

        await interaction.response.send_message(
            (
                "Ce Main est déjà associé "
                "à un autre compte Discord."
            ),
            ephemeral=True
        )

        return


    if resultat == "main_invalide":

        await interaction.response.send_message(
            "Le Main ne peut pas être vide.",
            ephemeral=True
        )

        return


# ============================================================
# COMMANDE : /defense
# ============================================================

@tree.command(
    name="defense",
    description="Enregistrer une défense de Perco ou Prisme"
)
@discord.app_commands.choices(
    type_defense=[
        discord.app_commands.Choice(
            name="Perco",
            value="perco"
        ),
        discord.app_commands.Choice(
            name="Prisme",
            value="prisme"
        )
    ]
)
async def defense(
    interaction: discord.Interaction,
    type_defense: discord.app_commands.Choice[str],
    screen1: discord.Attachment,
    screen2: discord.Attachment | None = None
):

    # --------------------------------------------------------
    # CONFIGURATION DU SALON
    # --------------------------------------------------------

    if interaction.guild_id is None:

        await interaction.response.send_message(
            "Cette commande doit être utilisée sur un serveur Discord.",
            ephemeral=True
        )

        return


    config = load_guild_config()


    guild_id = str(
        interaction.guild_id
    )


    guild_config = config.get(
        guild_id,
        {}
    )


    defense_channel_id = (
        guild_config.get(
            "defense_channel_id"
        )
    )


    if defense_channel_id is None:

        await interaction.response.send_message(
            (
                "Aucun salon de défense "
                "n'est configuré sur ce serveur.\n"
                "Un modérateur doit utiliser "
                "`/setchanneldefense`."
            ),
            ephemeral=True
        )

        return


    if (
        interaction.channel_id
        != defense_channel_id
    ):

        await interaction.response.send_message(
            (
                "Cette commande doit être "
                "utilisée dans le salon prévu "
                "pour les défenses."
            ),
            ephemeral=True
        )

        return


    # --------------------------------------------------------
    # DISCORD : LA COMMANDE PREND DU TEMPS
    # --------------------------------------------------------

    await interaction.response.defer()


    # --------------------------------------------------------
    # SCREENSHOTS
    # --------------------------------------------------------

    image_paths = []


    screen1_path = os.path.join(
        "screenshots",
        f"{interaction.id}_1_{screen1.filename}"
    )


    await screen1.save(
        screen1_path
    )


    image_paths.append(
        screen1_path
    )


    if screen2:

        screen2_path = os.path.join(
            "screenshots",
            f"{interaction.id}_2_{screen2.filename}"
        )


        await screen2.save(
            screen2_path
        )


        image_paths.append(
            screen2_path
        )


    # --------------------------------------------------------
    # CHARGER LES MEMBRES DE LA GUILDE
    # --------------------------------------------------------

    # Contrairement à l'ancienne version,
    # cette liste n'est PAS chargée au démarrage du bot.
    #
    # Elle est reconstruite depuis Data_joueurs
    # au moment où /defense est utilisée.
    players_nocta = charger_players_nocta(
    spreadsheet_base
    )


    # --------------------------------------------------------
    # OCR
    # --------------------------------------------------------

    gagnants, perdants, resultat = (
        analyser_combat(
            image_paths,
            players_nocta
        )
    )


    # --------------------------------------------------------
    # SÉPARATION DES JOUEURS
    # --------------------------------------------------------

    tous_joueurs = (
        gagnants + perdants
    )


    joueurs_nocta_dans_combat = []

    autres_joueurs = []


    for joueur in tous_joueurs:

        if joueur in players_nocta:

            joueurs_nocta_dans_combat.append(
                joueur
            )

        else:

            autres_joueurs.append(
                joueur
            )


    # --------------------------------------------------------
    # DONNÉES POUR LE SHEET
    # --------------------------------------------------------

    date_message = str(
        interaction.created_at.date()
    )


    type_combat = (
        type_defense.name
    )


    nocta_str = ", ".join(
        joueurs_nocta_dans_combat
    )


    autres_str = ", ".join(
        autres_joueurs
    )


    if resultat is None:

        resultat_final = (
            "Pas de résultat"
        )

    else:

        resultat_final = resultat


    # --------------------------------------------------------
    # MESSAGE DISCORD
    # --------------------------------------------------------

    confirmation = (
        await interaction.followup.send(
            (
                f"Défense {type_combat} "
                f"analysée : {resultat_final}"
            ),
            wait=True
        )
    )


    lien_discord = (
        confirmation.jump_url
    )


    # --------------------------------------------------------
    # GOOGLE SHEETS
    # --------------------------------------------------------

    worksheet_combat = (
        spreadsheet.worksheet(
            "combat"
        )
    )


    ligne = [
        date_message,
        type_combat,
        nocta_str,
        autres_str,
        resultat_final,
        lien_discord,
    ]


    worksheet_combat.append_row(
        ligne
    )


    # --------------------------------------------------------
    # CONFIRMATION FINALE
    # --------------------------------------------------------

    await confirmation.edit(
        content=(
            f"✅ Défense {type_combat} "
            f"enregistrée : {resultat_final}"
        )
    )


# ============================================================
# LANCEMENT
# ============================================================

client.run(token)