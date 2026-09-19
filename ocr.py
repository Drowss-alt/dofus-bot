"""
Module d'analyse OCR des combats Dofus.

Ce module utilise Tesseract OCR (via pytesseract) et Pillow pour extraire
les noms des joueurs gagnants et perdants à partir de screenshots de fin
de combat dans le jeu Dofus.

Fonction principale :
    analyser_combat() — Analyse 1 ou 2 screenshots et retourne les résultats.
"""

# ============================================================
# IMPORTATIONS DE MODULES STANDARD ET EXTERNES
# ============================================================
import platform

from PIL import Image          # Manipulation d'images (ouverture, rognage)
import pytesseract             # Interface Python pour Tesseract OCR


# ============================================================
# CONFIGURATION
# ============================================================

# Chemin vers l'exécutable Tesseract-OCR sur Windows.
# Cette configuration n'est nécessaire que si le chemin par défaut est incorrect.
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )


def analyser_combat(
    image_paths: list[str],
    players_nocta: list[str]
) -> tuple[list[str], list[str], str | None]:
    if len(image_paths) not in (1, 2):
        print("erreur : analyser_combat attend 1 ou 2 screenshots")
        return [], [], None
    """
    Analyse les screenshots d'un combat Dofus et extrait les résultats.

    Le premier screenshot contient à la fois les gagnants (haut) et les perdants
    (bas). Un deuxième screenshot optionnel peut fournir une liste complémentaire
    de perdants.

    Paramètres :
        image_paths   : liste des chemins vers les images (1 ou 2 screenshots).
        players_nocta : liste des noms des joueurs de l'alliance "Noctarium".

    Retourne :
        Un tuple (gagnants, perdants_total, resultat) où :
            - gagnants      : liste des noms de joueurs gagnants.
            - perdants_total: liste consolidée de tous les perdants.
            - resultat      : "Victoire", "Défaite" ou None si indéterminé.

    Exemple d'utilisation :
        >>> gagnants, perdants, res = analyser_combat(
        ...     ["screen1.png", "screen2.png"],
        ...     ["JoueurA", "JoueurB"]
        ... )
    """

    # ============================================================
    # PARTIE 1 : ANALYSE DU 2ÈME SCREENSHOT (PERDANTS)
    # ============================================================

    perdants_2: list[str] = []

    if len(image_paths) == 2:
        image = Image.open(image_paths[1])

        # Zone de rognage : coordonnées (x_gauche, y_haut, x_droite, y_bas)
        zone_noms = image.crop((90, 580, 300, 829))

        text = pytesseract.image_to_string(
            zone_noms,
            lang="fra+eng",       # OCR en français ET anglais
            config="--psm 6"      # Mode : bloc de texte uniforme
        )

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        headers: list[int] = []

        for number, line in enumerate(lines):
            if "personnage" in line.lower() or "personage" in line.lower():
                headers.append(number)

        if headers:
            perdants_2 = lines[headers[0] + 1:]
        else:
            print("erreur OCR : header du screen 2 introuvable")

    # ============================================================
    # PARTIE 2 : ANALYSE DU PREMIER SCREENSHOT (GAGNANTS + PERDANTS)
    # ============================================================

    image = Image.open(image_paths[0])
    zone_noms = image.crop((90, 145, 300, 829))

    text = pytesseract.image_to_string(
        zone_noms,
        lang="fra+eng",
        config="--psm 6"
    )

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    headers: list[int] = []

    for number, line in enumerate(lines):
        if "personnage" in line.lower() or "personage" in line.lower():
            headers.append(number)

    # ============================================================
    # VALIDATION DU RÉSULTAT OCR
    # ============================================================

    ocr_valide = (
        len(headers) == 2                    # Deux headers trouvés
        and headers[1] - headers[0] > 2      # Séparation suffisante
        and len(lines) > headers[1] + 1      # Contenu après le 2e header
    )

    if not ocr_valide:
        # Tentative avec une zone de rognage réduite pour éviter les parasites
        zone_noms = image.crop((90, 145, 300, 600))

        text = pytesseract.image_to_string(
            zone_noms,
            lang="fra+eng",
            config="--psm 6"
        )

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        headers = []

        for number, line in enumerate(lines):
            if "personnage" in line.lower() or "personnage" in line.lower():
                headers.append(number)

        ocr_valide = (
            len(headers) == 2
            and headers[1] - headers[0] > 2
            and len(lines) > headers[1] + 1
        )

        if not ocr_valide:
            print("erreur OCR : impossible d'extraire les joueurs (screen 1)")
            return [], [], None

    # ============================================================
    # EXTRACTION DES NOMS DE JOUEURS
    # ============================================================

    perdants_1 = lines[headers[1] + 1:]
    gagnants = lines[headers[0] + 1 : headers[1] - 1]

    # ============================================================
    # COMPILATION DES PERDANTS (SCREEN 1 + SCREEN 2)
    # ============================================================

    perdants_total: list[str] = []

    for perdant in perdants_1:
        if perdant not in perdants_total:
            perdants_total.append(perdant)

    for perdant in perdants_2:
        if perdant not in perdants_total:
            perdants_total.append(perdant)

    # ============================================================
    # DÉTERMINATION DU RÉSULTAT POUR NOCTARIUM
    # ============================================================

    resultat: str | None = None

    nocta_gagnant = any(
    player in gagnants
    for player in players_nocta
    )

    nocta_perdant = any(
        player in perdants_total
        for player in players_nocta
    )

    if nocta_gagnant and not nocta_perdant:
        resultat = "Victoire"

    elif nocta_perdant and not nocta_gagnant:
        resultat = "Défaite"

    else:
        resultat = None
        # ============================================================
        # RETOUR DES RÉSULTATS
        # ============================================================

    return gagnants, perdants_total, resultat
