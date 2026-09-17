# ============================================================
# IMPORTATIONS DE MODULES (bibliothèques externes)
# ============================================================
import os                    # Permet de manipuler le système de fichiers (dossiers, variables d'environnement)
import gspread               # Bibliothèque pour lire/écrire sur Google Sheets
import discord               # Bibliothèque pour interagir avec Discord API
from dotenv import load_dotenv  # Permet de charger les variables depuis un fichier .env
from ocr import analyser_combat  # Importe notre fonction d'analyse d'image (définie dans ocr.py)

# ============================================================
# CHARGEMENT DES VARIABLES D'ENVIRONNEMENT
# ============================================================
load_dotenv()  # Lit le fichier .env et ajoute les variables au système

# ============================================================
# CONFIGURATION GOOGLE SHEETS
# ============================================================

# Récupère l'URL de la Google Sheet depuis le fichier .env
sheet_url = os.getenv("GOOGLE_SHEET_URL")

# Initialise gspread avec tes identifiants (fichier credentials.json)
# Ce fichier contient les clés API pour accéder à ton Google Account
google = gspread.service_account(filename="credentials.json")

# Ouvre la sheet spécifique grâce à son URL
spreadsheet = google.open_by_url(sheet_url)

# Sélectionne la feuille "Nocta" où sont listés les joueurs de Noctarium
worksheet = spreadsheet.worksheet("Nocta")

# Récupère TOUTE la colonne A (index 1 car Python compte à partir de 0)
players_nocta = worksheet.col_values(1)

# On enlève la première ligne qui est le titre ("Joueur" par exemple)
players_nocta = players_nocta[1:]


# ============================================================
# CONFIGURATION DU BOT DISCORD
# ============================================================

# Récupère le token Discord (mot de passe du bot) depuis .env
token = os.getenv("DISCORD_TOKEN")

# ID du canal Discord où le bot doit écouter les messages
channel_id = int(os.getenv("CHANNEL_ID"))

# Crée un dossier "screenshots" pour sauvegarder les images si il n'existe pas
os.makedirs("screenshots", exist_ok=True)

# Configure les "intentions" du bot (ce qu'il a le droit de faire/voir)
intents = discord.Intents.default()
intents.message_content = True  # Autorise le bot à lire le contenu des messages

# Crée et initialise le client Discord (c'est lui qui va se connecter)
client = discord.Client(intents=intents)

tree = discord.app_commands.CommandTree(client)

# ============================================================
# ÉVÉNEMENT : QUAND LE BOT SE CONNECTE
# ============================================================
synced = False

@client.event  # Décorateur : indique que cette fonction gère un événement Discord
async def on_ready():  # Fonction appelée automatiquement quand le bot est prêt
    global synced

    if not synced:
        await tree.sync()
        synced = True
        print("commandes slash synchronisées")

    print(f"Bot connecté : {client.user}")  # Affiche le nom du bot


# ============================================================
# LANCEMENT DU BOT
# ============================================================
@tree.command(
    name="defense",
    description="Enregistrer une défense de perco ou prisme"
)
@discord.app_commands.choices(
    type_defense=[
        discord.app_commands.Choice(name="Perco", value="perco"),
        discord.app_commands.Choice(name="Prisme", value="prisme")
    ]
)
async def defense(
    interaction: discord.Interaction,
    type_defense: discord.app_commands.Choice[str],
    screen1: discord.Attachment,
    screen2: discord.Attachment | None = None
):

    if 1547704041440682066 != channel_id:
        await interaction.response.send_message(
            "Cette commande doit être utilisée dans le salon prévu pour les défenses.",
            ephemeral=True
        )
        return

    # Dit à Discord que le bot travaille.
    # Ça évite que Discord considère la commande comme expirée
    # pendant que Tesseract analyse les images.
    await interaction.response.defer()

    # Liste qui sera envoyée à analyser_combat()
    image_paths = []

    # ========================================================
    # SCREEN 1
    # ========================================================

    # On crée un nom unique grâce à interaction.id.
    # Cela évite d'écraser une ancienne image ayant le même nom.
    screen1_path = os.path.join(
        "screenshots",
        f"{interaction.id}_1_{screen1.filename}"
    )

    # Télécharge le screen 1
    await screen1.save(screen1_path)

    # Ajoute son chemin à la liste
    image_paths.append(screen1_path)


    # ========================================================
    # SCREEN 2 OPTIONNEL
    # ========================================================

    if screen2:

        screen2_path = os.path.join(
            "screenshots",
            f"{interaction.id}_2_{screen2.filename}"
        )

        # Télécharge le screen 2
        await screen2.save(screen2_path)

        # Ajoute son chemin après le screen 1
        image_paths.append(screen2_path)

    # ========================================================
    # ANALYSE DES IMAGES
    # ========================================================

    gagnants, perdants, resultat = analyser_combat(
        image_paths,
        players_nocta
    )

    # ========================================================
    # PRÉPARATION DES DONNÉES
    # ========================================================

    # Regroupe tous les participants du combat
    tous_joueurs = gagnants + perdants

    # Sépare les joueurs Noctarium des autres
    joueurs_nocta_dans_combat = []
    autres_joueurs = []

    for joueur in tous_joueurs:
        if joueur in players_nocta:
            joueurs_nocta_dans_combat.append(joueur)
        else:
            autres_joueurs.append(joueur)

    # Date de la commande
    date_message = str(interaction.created_at.date())

    # Le menu Discord nous donne directement "Perco" ou "Prisme"
    type_combat = type_defense.name

    # Transforme les listes Python en texte pour Google Sheets
    nocta_str = ", ".join(joueurs_nocta_dans_combat)
    autres_str = ", ".join(autres_joueurs)

    # Sécurité si l'OCR n'a pas trouvé le résultat
    if resultat is None:
        resultat_final = "Pas de résultat"
    else:
        resultat_final = resultat


    # ========================================================
    # MESSAGE DE CONFIRMATION DISCORD
    # ========================================================

    confirmation = await interaction.followup.send(
        f"Défense {type_combat} analysée : {resultat_final}",
        wait=True
    )

    # Lien vers le message de confirmation Discord
    lien_discord = confirmation.jump_url


    # ========================================================
    # ÉCRITURE DANS GOOGLE SHEETS
    # ========================================================

    worksheet_combat = spreadsheet.worksheet("combat")

    ligne = [
        date_message,
        type_combat,
        nocta_str,
        autres_str,
        resultat_final,
        lien_discord
    ]

    worksheet_combat.append_row(ligne)


    # ========================================================
    # DEBUG POWERSHELL
    # ========================================================

    print("===================================")
    print("Type :", type_combat)
    print("Noctarium :", nocta_str)
    print("Autres :", autres_str)
    print("Résultat :", resultat_final)
    print("===================================")

    # Modifie le message Discord une fois l'enregistrement terminé
    await confirmation.edit(
        content=f"✅ Défense {type_combat} enregistrée : {resultat_final}"
    )

client.run(token)  # Démarre le bot et le garde connecté en permanence