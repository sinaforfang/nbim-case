import pandas as pd
from .schema import to_canonical, NBIM_MAP, CUST_MAP

def load_csvs(nbim_path: str, custody_path: str):
    def read_semicolon(path: str) -> pd.DataFrame:
        try:
            return pd.read_csv(path, sep=";", engine="python")
        except UnicodeDecodeError:
            return pd.read_csv(path, sep=";", engine="python", encoding="ISO-8859-1")

    nbim = read_semicolon(nbim_path)
    custody = read_semicolon(custody_path)
    
    print("Files read")

    nb = to_canonical(nbim, NBIM_MAP)
    cu = to_canonical(custody, CUST_MAP)
    print("Mapping done")
    return nb, cu
