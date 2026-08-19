from pathlib import Path
import pandas as pd

from processing import (
    load_and_clean_excel,
    compute_retrocessions,
)

FILE = Path("data/export-lc.xls")

IK_VALUE = 0.61
IF_VALUE = 4.00
MD_VALUE = 10.00


def main():
    print(f"Chargement : {FILE}")

    # ----------------------------------------
    # 1. Lecture du fichier
    # ----------------------------------------
    df = load_and_clean_excel(FILE)

    print("\n=== DATAFRAME BRUT ===")
    print(df.head())

    # ----------------------------------------
    # 2. Calcul des rétrocessions
    # ----------------------------------------
    results = compute_retrocessions(
        df=df,
        ik_value=IK_VALUE,
        if_value=IF_VALUE,
        md_value=MD_VALUE,
    )

    # ----------------------------------------
    # 3. Affichage du résultat
    # ----------------------------------------
    result_df = pd.DataFrame(results)

    print("\n=== RESULTATS ===")
    print(result_df)


if __name__ == "__main__":
    main()