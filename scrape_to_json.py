import os
from bs4 import BeautifulSoup
from tqdm import tqdm
import re
import zipfile
import tiktoken
import json

#used with the following torrent magnet:?xt=urn:btih:8d5414c57f28fad5774f0dbba8f2aae8ae3cec4b&dn=Officially%20Translated%20Light%20Novels%20%28LNs%29%20v21.0&tr=http%3A%2F%2Fnyaa.tracker.wf%3A7777%2Fannounce&tr=udp%3A%2F%2Fopen.stealth.si%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Fexodus.desync.com%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.torrent.eu.org%3A451%2Fannounce

download_location = r"/path/to/files"
size = 1024 #rough size of desired output in tokens, here 1k tokens

def strip(html):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup(["img", "style", "title"]):
        script.extract()
    return ''.join(soup.strings)

r = re.compile(r'OEBPS\/Text\/(chapter.*|epilogue\..*|prologue\..*)|OPS\/section-\d{3}.*') #matches newer OPS and older OEBPS formats
blank = re.compile(r'[\t\n\r ]*')

tokenizer = tiktoken.get_encoding("o200k_base") #gpt 3.5 tokeniser, close enough
out = []

for root, dirs, files in tqdm(list(os.walk(download_location))):
    for file in files:
        outtext = ""
        length = 0
        publisher = file.replace("]", "[").split("[")[1]
        if file[-5:] == ".epub": #if epub
            with (zipfile.ZipFile(os.path.join(root, file), mode="r") as archive):
                unsorted = list(filter(r.match, archive.namelist()))
                p = False
                e = False
                sorted = unsorted.copy()
                for item in unsorted:
                    if item.startswith("OEBPS/Text/prologue"):
                        p = item
                        sorted.remove(item)
                    elif item.startswith("OEBPS/Text/epilogue"):
                        e = item
                        sorted.remove(item)
                sorted.sort()
                if p:
                    sorted.insert(0, p)
                if e:
                    sorted.append(e)
                
                if publisher == "Seven Seas": #broadly, at the risk of removing
                    del sorted[0:4]
                    del sorted[-2:]

                for textfile in sorted:
                    text = strip(archive.read(textfile))
                    if not blank.fullmatch(text):
                        text = text.replace(r'“', r'"').replace(r'”', r'"').replace(r'‘', r"'").replace(r'’', r"'").replace("\r\n", r'\n')
                        text = re.sub(r'(?:\n[ \t]*){3,}', r'\n', text) #gets rid of excessive \n
                        text = re.sub(r'(?:[ \t]){2,}', r' ', text) #gets rid of excessive whitespace
                        text = re.sub("[^\x00-\x7F]+","",text) #gets rid of control characters

                        #print out/carry on if needed, first split by sentence
                        textlist = re.split(r'([.?!]+[ \t\n]*)', text)
                        if not (len(textlist) % 2 == 0):
                            textlist.append("")
                        for i in range(len(textlist)//2):
                            item = textlist[i*2]+textlist[(i*2)+1]
                            new_length = len(tokenizer.encode(item)) #by considering the individual sentences rather than the whole chunk, there will be more tokens counted than actual, so size is not exceeded often
                            if length + new_length >= size:
                                out.append({"text":outtext})
                                outtext = ""
                                length = 0
                            else:
                                outtext += item
                                length += new_length
                #final flush per epub
                if not blank.fullmatch(outtext):
                    out.append({"text": outtext})
                outtext = ""
                length = 0

with open(f"nyaa{str(size)[:-3]}k.json", "w", encoding='utf-8') as f2w:
    json.dump(out, f2w, ensure_ascii=True, indent=4)
