from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def scrape_article(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.find("h1")
    paragraphs = soup.find_all("p")

    content = ""
    for p in paragraphs:
        content += p.get_text() + "\n"

    return {
        "title": title.get_text() if title else "No title found",
        "content": content[:1000]
    }

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.json
    page_type = data["type"]
    url = data["url"]

    if page_type == "article":
        result = scrape_article(url)
        return jsonify(result)

    return jsonify({"error": "Page type not supported"})

if __name__ == "_main_":
    app.run(debug=True)