let selectedType = "";

function selectPageType(type) {
  selectedType = type;
  const el = document.getElementById("selectedType");
  if (el) el.innerText = "Selected page type: " + type;
}

function startScraping() {
  const url = document.getElementById("urlInput").value;

  if (!selectedType) {
    alert("Please select a page type first");
    return;
  }

  if (!url) {
    alert("Please enter a URL");
    return;
  }

  // show result box immediately so user gets feedback
  document.getElementById("result").style.display = "block";
  document.getElementById("articleTitle").innerText = "Loading...";
  document.getElementById("articleContent").innerText = "Working...";

  fetch("http://127.0.0.1:5000/scrape", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      type: selectedType,
      url: url,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        document.getElementById("articleTitle").innerText = "Error";
        document.getElementById("articleContent").innerText = data.error;
        return;
      }

      if (selectedType === "article") {
        document.getElementById("articleTitle").innerText = data.title || "No title";
        document.getElementById("articleContent").innerText = data.content || "No content";
      }

      if (selectedType === "product") {
        document.getElementById("articleTitle").innerText = data.title || "No title";
        document.getElementById("articleContent").innerText =
          "Price: " + (data.price || "") + "\n\n" + (data.description || "");
      }
      
      if (selectedType === "listing") {
        document.getElementById("articleTitle").innerText = "Listing results";
        const items = data.items || [];
        if (!items.length) {
          document.getElementById("articleContent").innerText = data.error || 'No items found';
        } else {
          const html = items.map(it => {
            const img = it.image ? `<img src="${it.image}" style="max-width:72px;max-height:72px;margin-right:8px;"/>` : '';
            const price = it.price ? `<div style="font-weight:600;color:#00ffd5">${it.price}</div>` : '';
            const link = it.url ? `<a href="${it.url}" target="_blank" rel="noopener">${it.title}</a>` : `${it.title}`;
            return `<div style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.04);">${img}<div><div>${link}</div>${price}<div style="color:#ddd;margin-top:6px">${it.snippet || ''}</div></div></div>`;
          }).join('');
          document.getElementById("articleContent").innerHTML = html;
        }
      }
    })
    .catch((error) => {
      console.error(error);
      alert("Check console (F12)");
    });
}