from fastapi import FastAPI, Query, Request
from crawler import PttWebCrawler

app = FastAPI()
crawler = PttWebCrawler()

@app.get("/crawl")
def crawl(board: str, start: int = Query(...), end: int = Query(...)):
    articles = crawler.parse_articles(start, end, board)
    return {"articles": articles}

@app.get("/latest_index")
def latest_index(board: str):
    try:
        index = PttWebCrawler.getLastPage(board)
        return index
    except Exception as e:
        return {"error": str(e)}