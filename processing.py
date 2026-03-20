import pandas as pd
import logging

logger = logging.getLogger(__name__)

KNOWN_SF_WITH_DOT = {
    "SF7.5",
    "SF11.6",
    "SF12.5",
    "SF12.6",
    "SF15.6",
    "SF16.5",
    "SF19.5",
    "SF22.6",
}

RETROCESSIONS_VARIABLES = {
    "IK": 0.61,
    "IF": 4,
    "MD": 10
}

KNOWN_SF_COMPRESSED = {
    sf.replace(".", "") for sf in KNOWN_SF_WITH_DOT
}

def fix_sf_code(acte: str):
    """
    Corrige uniquement les SF connus comme devant avoir un point.
    Exemple :
    SF165 -> SF16.5
    SF12 -> reste SF12
    """
    if not acte.startswith("SF"):
        return acte

    if acte in KNOWN_SF_WITH_DOT:
        return acte  # déjà correct

    if acte in KNOWN_SF_COMPRESSED:
        # reconstruire avec le point
        val = acte[2:]
        return f"SF{val[:-1]}.{val[-1]}"
    
    if acte.startswith("SF") and acte not in KNOWN_SF_WITH_DOT and acte not in KNOWN_SF_COMPRESSED:
        logger.info(f"SF inconnu rencontré (laissé tel quel): {acte}")

    # sinon on laisse tel quel (nouveau SF ou valide)
    return acte


def parse_actes(actes_str):
    """
    MaieuticApp renvoie l'ensemble des actes cotés dans une même colonne,
    séparés par une virgule (eg. "SF125, MD, IKP")
    On parse ici l'ensemble de ces actes.
    """
    actes = [a.strip() for a in actes_str.split(",")]

    fixed_actes = []

    for a in actes:
        fixed = fix_sf_code(a)

        if a == "IKM":
            logger.warning("WARNING : IKM détecté (anormal en Bretagne)")

        fixed_actes.append(fixed)

    return fixed_actes


def load_and_clean_excel(file):
    df = pd.read_excel(file, header=None)

    # Il semble que la première ligne soit toujours vide, dans le doute
    # on parse les lignes jusqu'à trouver un tableau,
    # la première ligne est traitée comme un header
    first_row = df.dropna(how="all").index[0]
    df.columns = df.iloc[first_row]
    df = df.iloc[first_row + 1 :]

    df.columns = df.columns.str.strip()

    df.rename(
        columns={
            "numero adeli": "numero_adeli",
            "actes": "actes",
            "ik qte": "ik_qte",
            "c msf type": "type_consultation",
            "honoraire": "honoraire",
            "remplacant·e": "rempla",
        },
        inplace=True,
    )

    df = df.reset_index(drop=True)

    return df


def compute_retrocessions(df, ik_value=RETROCESSIONS_VARIABLES["IK"], if_value=RETROCESSIONS_VARIABLES["IF"], md_value=RETROCESSIONS_VARIABLES["MD"]):
    """
    Fonction de calcul des rétrocessions prenant en compte la logique métier suivante :
    Les IF, IK et MD doivent être traitées à part du montant total des honoraires.

    Input de la fonction : Dataframe telle que renvoyée par load_and_clean_excel()
    """
    results = {}

    for _, row in df.iterrows():
        # On boucle ligne par ligne, chaque ligne correspondans à un acte, une patiente, une facturation

        # Le numéro ADELI et la colonne rempla permettent
        # d'identifier les sages-femmes à l'origine de l'acte
        key = (row["numero_adeli"], row["rempla"])

        # On initialise l'aggrégation et les valeurs de total pour toute sage-femme
        # n'étant pas encore dans `results`
        if key not in results:
            results[key] = {"total": 0, "total_sans_indemnites": 0, "total_ik_if_md": 0}

        actes = parse_actes(row["actes"])
        honoraires = float(row["honoraire"])
        ik_qte = float(row.get("ik_qte", 0) or 0)

        total = honoraires
        deduction = 0

        # Calcul des IK (ik_qte * valeur des IK)
        if any(a in ["IK", "IKP"] for a in actes):
            deduction += ik_qte * ik_value

        # IF
        if "IF" in actes:
            deduction += if_value

        # MD
        if "MD" in actes:
            deduction += md_value

        total_sans = total - deduction

        results[key]["total"] += total
        results[key]["total_sans_indemnites"] += total_sans
        results[key]["total_ik_if_md"] += deduction

    # Calculs finaux
    final = []
    for (adeli, rempla), data in results.items():
        final.append(
            {
                "adeli": adeli,
                "rempla": rempla,
                "total": round(data["total"], 2),
                "indemnites": round(data["total_ik_if_md"], 2),
                "retro_30": round(data["total_sans_indemnites"] * 0.3, 2),
                "retro_40": round(data["total"] * 0.4, 2),
            }
        )

    return final
