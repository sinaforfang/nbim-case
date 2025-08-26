import pandas as pd
from .schema import to_canonical, NBIM_MAP, CUST_MAP

def load_csvs(nbim_path: str, custody_path: str):
    # read csv files and return dfs with columns renamed
    def read_semicolon(path: str) -> pd.DataFrame:
        try:
            return pd.read_csv(path, sep=";", engine="python")
        except UnicodeDecodeError:
            return pd.read_csv(path, sep=";", engine="python", encoding="ISO-8859-1")

    # read files
    nbim = read_semicolon(nbim_path)
    custody = read_semicolon(custody_path)
    
    # rename the columns
    nb = to_canonical(nbim, NBIM_MAP)
    cu = to_canonical(custody, CUST_MAP)
    return nb, cu
