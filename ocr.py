# ============================================================
# IMPORTATIONS ET CONFIGURATION
# ============================================================
import pytesseract  # Bibliothèque qui utilise Tesseract OCR pour extraire du texte d'images
from PIL import Image  # Pillow : bibliothèque pour manipuler les images (ouvrir, rogner, etc.)
import platform
# Indique à pytesseract où trouver le programme Tesseract sur ton ordi
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )


# ============================================================
# FONCTION PRINCIPALE : ANALYSER UN COMBAT
# ============================================================
def analyser_combat(image_paths, players_nocta):
    """
    Analyse les screenshots d'un combat Dofus et extrait :
    - La liste des gagnants
    - La liste des perdants
    - Le résultat (Victoire ou Défaite pour Noctarium)
    
    Paramètres :
      - image_paths : liste des chemins vers les images (2 screenshots)
      - players_nocta : liste des joueurs de Noctarium pour comparer
    
    Retourne :
      - gagnants : liste des noms de joueurs gagnants
      - perdants : liste des noms de joueurs perdants
      - resultat : "Victoire", "Défaite" ou None
    """

    # ============================================================
    # PARTIE 1 : ANALYSE DU 2ÈME SCREENSHOT (PERDANTS)
    # ============================================================
    
    perdants_2 = []  # Liste vide pour stocker les perdants du screen 2
    
    if len(image_paths) == 2:  # Si on a bien 2 images (sinon on saute cette partie)
        
        # Ouvre la deuxième image (index 1 car Python compte à partir de 0)
        image = Image.open(image_paths[1])
        
        # "Rogner" l'image : ne garder que la zone où sont les noms des perdants
        # Les coordonnées (90, 580, 300, 829) définissent un rectangle dans l'image
        # (x_gauche, y_haut, x_droite, y_bas)
        zone_noms = image.crop((90, 580, 300, 829))

        # Extrait le texte de la zone rogée avec Tesseract OCR
        text = pytesseract.image_to_string(
            zone_noms,
            lang="fra+eng",  # Le OCR doit lire en français ET anglais
            config="--psm 6"  # Configuration du mode de lecture (bloc uniforme)
        )

        # Découpe le texte en lignes et enlève les lignes vides
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        
        # Cherche la position des mots "personnage" dans le texte
        HEADERS = []  # Liste vide pour stocker les numéros de ligne des headers
        
        for number, line in enumerate(lines):
            # enumerate() donne à la fois l'index (number) et le contenu (line)
            if "personnage" in line.lower() or "personage" in line.lower():  # .lower() met tout en minuscule pour comparer
                HEADERS.append(number)  # Ajoute le numéro de ligne où on trouve "personnage"

        # Si on a trouvé des headers, on extrait les noms après le premier header
        if HEADERS:
            perdants_2 = lines[HEADERS[0] + 1:]  # Prend tout après la première occurrence
        else:
            print("erreur OCR : headere du screen 2 introuvable")

    # ============================================================
    # PARTIE 2 : ANALYSE DU PREMIER SCREENSHOT (GAGNANTS + PERDANTS)
    # ============================================================
    
    image = Image.open(image_paths[0])  # Ouvre le premier screenshot
    
    # On rogne la zone où se trouvent les noms (gagnants en haut, perdants en bas)
    zone_noms = image.crop((90, 145, 300, 829))

    text = pytesseract.image_to_string(
        zone_noms,
        lang="fra+eng",
        config="--psm 6"
    )

    # Même traitement : on sépare le texte en lignes non vides
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    HEADERS = []  # On va chercher les deux headers "personnage" (un pour gagnants, un pour perdants)
    
    for number, line in enumerate(lines):
        if "personnage" in line.lower() or "personage" in line.lower():
            HEADERS.append(number)

  
    # ============================================================
    # VALIDATION DU RÉSULTAT OCR
    # ============================================================
    
    # On vérifie que le résultat est cohérent :
    # - Il doit y avoir exactement 2 headers ("personnage")
    # - Ils doivent être séparés d'au moins 2 lignes (sinon c'est un bug de lecture)
    # - Il doit y avoir du texte après le deuxième header
    ocr_valide = (
        len(HEADERS) == 2                    # On a bien trouvé 2 headers
        and HEADERS[1] - HEADERS[0] > 2     # Ils sont suffisamment éloignés
        and len(lines) > HEADERS[1] + 1     # Il y a du contenu après le 2ème header
    )

    # Si le résultat n'est pas valide, on essaie une zone de rognage différente
    if not ocr_valide:
        # On rogne plus petit (jusqu'à y=600 au lieu de 829) pour éviter les zones parasites
        zone_noms = image.crop((90, 145, 300, 600))

        text = pytesseract.image_to_string(
            zone_noms,
            lang="fra+eng",
            config="--psm 6"
        )

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        HEADERS = []

        for number, line in enumerate(lines):
            if "personnage" in line.lower() or "peresonage" in line.lower():
                HEADERS.append(number)

        # On re-vérifie si le nouveau résultat est valide
        ocr_valide = (
            len(HEADERS) == 2
            and HEADERS[1] - HEADERS[0] > 2
            and len(lines) > HEADERS[1] + 1
        )

        # Si ça échoue encore, on arrête et on retourne des valeurs vides
        if not ocr_valide:
            print("erreur OCR : impossible d'extraire les joueurs (screen 1)")
            return [], [], None  # Retourne listes vides et resultat None

    # ============================================================
    # EXTRACTION DES NOMS DE JOUEURS
    # ============================================================
    
    # Les perdants du screen 1 sont après le deuxième header
    perdants_1 = lines[HEADERS[1] + 1:]
    
    # Les gagnants sont entre le premier et le deuxième header
    gagnants = lines[HEADERS[0] + 1 : HEADERS[1] - 1]
    # Note : HEADERS[1] - 1 car on ne veut pas inclure la ligne "personnage" suivante

    # ============================================================
    # COMPILATION DES PERDANTS (SCREEN 1 + SCREEN 2)
    # ============================================================
    
    perdants_total = []  # Liste qui va contenir tous les perdants des deux screens
    
    for perdant in perdants_1:
        if perdant not in perdants_total:  # On évite les doublons
            perdants_total.append(perdant)

    # ============================================================
    # DÉTERMINATION DU RÉSULTAT POUR NOCTARIUM
    # ============================================================
 

    resultat = None  # Par défaut, on ne sait pas encore

    # Si un joueur de Noctarium est dans la liste des perdants → Défaite
    for perdant in perdants_2:
        if perdant not in perdants_total:  # On évite les doublons avec screen 1
            perdants_total.append(perdant)

    for player in players_nocta:
        if player in perdants_total:
            resultat = "Défaite"
    
    # Si un joueur de Noctarium est dans la liste des gagnants → Victoire
    for player in players_nocta:
        if player in gagnants:
            resultat = "Victoire"

    # ============================================================
    # RETOUR DES RÉSULTATS
    # ============================================================
    
    return gagnants, perdants_total, resultat
