import logging 
import sys  
from pathlib import Path 

def get_logger(name: str, log_file: str = "log/Pipeline_log.log") -> logging.Logger:
    logger = logging.getLogger(name)    
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger   
    file_fmt = logging.Formatter(
        fmt = "%(asctime)s | %(levelname)-8s | [%(funcName)s:%(lineno)d] | %(message)s",
        datefmt = "%H:%M:%S"
    )
    console_fmt = logging.Formatter(
        fmt = "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt= "%H:%M:%S"
    )

    Path(log_file).parent.mkdir(parents=True,exist_ok=True)
    
    stream_hd = logging.StreamHandler()
    stream_hd.setFormatter(console_fmt)
    stream_hd.setLevel(logging.INFO)

    file_hd = logging.FileHandler(log_file, mode= "a", encoding="utf-8")
    file_hd.setFormatter(file_fmt)
    file_hd.setLevel(logging.DEBUG)

    logger.addHandler(stream_hd)
    logger.addHandler(file_hd) 

    return logger   