import os
import shutil
import sys
import config
from typing import List
from argparse import ArgumentParser
from genericpath import exists

def main(cli_args: List[str]):
    parser = ArgumentParser()
    parser.add_argument("--elastic", required=True) # elastic url
    parser.add_argument("--user", required=True)    # elastic user
    parser.add_argument("--pw", required=True)    # elastic pass
    parser.add_argument("--start", required=True)   # start epoch
    parser.add_argument("--end", required=True)     # end epoch

    args = parser.parse_args(cli_args)

    if exists(config.index_folder):
        shutil.rmtree(config.index_folder)
    os.mkdir(config.index_folder)

    for epoch in range(int(args.start), int(args.end) + 1):
        print(f"Getting index for epoch {epoch}:")
        os.system(f"./index_dumper {args.elastic} accounts-000001_{epoch} {args.user} {args.pw}")
        
        if not exists(config.index_export):
            print(f"Index for epoch {epoch} not retrieved!")
            return
        
        new_name = f'{config.index_export.split(".")[0]}_{epoch}.{config.index_export.split(".")[1]}'
        os.rename(config.index_export, f"{config.index_folder}/{new_name}")
    
    print(f"All indexes retrieved and stored in: {config.index_folder}")


if __name__ == "__main__":
    main(sys.argv[1:])

# Usage:
# python3 indexes_fetcher.py --elastic="link" --user=user --pw=pass --start=650 --end=651