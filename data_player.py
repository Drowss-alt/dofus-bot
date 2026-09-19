"""
Module de gestion des données joueurs.

Fournit des fonctions pour interagir avec la feuille Google Sheets
"Data_joueurs".
"""


# ============================================================
# CHARGEMENT DES JOUEURS
# ============================================================

def charger_joueurs(spreadsheet_base):

    worksheet = spreadsheet_base.worksheet("Data_joueurs")

    # get_all_values() récupère toutes les lignes.
    # [1:] enlève la première ligne contenant les titres.
    return worksheet.get_all_values()[1:]


# ============================================================
# RECHERCHE PAR DISCORD ID
# ============================================================

def trouver_main_par_id(player_list, discord_id):

    for player in player_list:

        # On vérifie que la ligne va bien jusqu'à la colonne H.
        if len(player) < 8:
            continue

        # Colonne H = Discord_ID
        if str(discord_id) == player[7]:

            # Colonne A = Main
            return player[0]

    return None


# ============================================================
# RECHERCHE PAR MAIN
# ============================================================

def trouver_id_par_main(player_list, main):

    for player in player_list:

        if len(player) < 8:
            continue

        # Colonne A = Main
        if main == player[0]:

            # Colonne H = Discord_ID
            return player[7]

    return None


# ============================================================
# ATTRIBUTION D'UN MAIN
# ============================================================

def attribuer_main(spreadsheet_base, discord_id, main):

    # Enlève les espaces accidentels avant/après.
    main = main.strip()

    if main == "":
        return "main_invalide"

    # On charge la feuille UNE seule fois.
    player_list = charger_joueurs(spreadsheet_base)

    main_existant = trouver_main_par_id(
        player_list,
        discord_id
    )

    id_existant = trouver_id_par_main(
        player_list,
        main
    )

    # Ni l'ID ni le Main ne sont déjà utilisés.
    if main_existant is None and id_existant is None:

        worksheet_data_player = spreadsheet_base.worksheet(
            "Data_joueurs"
        )

        # A Main
        # B Classes
        # C Stuff
        # D Guilde
        # E Alliance
        # F Gigalodon
        # G Sanctuaire
        # H Discord_ID
        ligne = [
            main,
            "",
            "",
            False,
            False,
            False,
            False,
            str(discord_id),
        ]

        worksheet_data_player.append_row(ligne)

        return "OK"

    # L'ID Discord possède déjà un Main.
    if main_existant is not None:
        return "Discord_ID_existant"

    # Le Main appartient déjà à un autre ID.
    if id_existant is not None:
        return "main_existant"


# ============================================================
# JOUEURS NOCTARIUM UTILISÉS PAR L'OCR
# ============================================================

def charger_players_nocta(spreadsheet_base):

    player_list = charger_joueurs(spreadsheet_base)

    players_nocta = []

    for player in player_list:

        if len(player) < 4:
            continue

        main = player[0]

        # Colonne D = Guilde
        guilde = player[3]

        if guilde.strip().upper() == "TRUE":

            if main:
                players_nocta.append(main)

    return players_nocta