import json
import os

from bs4 import BeautifulSoup
import requests

OUTPUT_FILENAME = os.environ["FILENAME"]


class ForProgrammersScraper:
    def __init__(self, filename=None):
        self.filename = OUTPUT_FILENAME if filename is None else filename
        with open(self.filename, "rb") as jfile:
            self.json_data = json.load(jfile)

    def get_offers_from_forprogrammers(self):
        response = requests.get("https://4programmers.net/Praca?q=Python&city=Warszawa")
        soup = BeautifulSoup(response.content, "html.parser")
        links = [f.get("href") for f in soup.find_all("a")]
        # TODO: change hard-coded '3' onto an integer 'regex'
        job_prefix = "https://4programmers.net/Praca/3"
        job_links = [
            link
            for link in links
            if isinstance(link, str) and link.startswith(job_prefix)
        ]
        for job_link in job_links:
            if job_link not in self.json_data:
                self.get_offer_details(job_link)
        with open(self.filename, "w") as jfile:
            json.dump(self.json_data, jfile)

    def get_offer_details(self, link):
        print(f"Scrapping webpage {link}")
        response = requests.get(link)
        soup = BeautifulSoup(response.content, "html.parser")
        job_title = soup.find(attrs={"class": "media-heading"}).text
        offerer = soup.find(attrs={"class": "employer"}).text
        # TODO: handle each part of payment separately
        payment = soup.find(attrs={"class": "salary pull-right"})
        if payment is not None:
            payment = (
                payment.text.replace("\n    \n", "\t")
                .replace(" ", "")
                .replace("\n", "")
                .replace("\t", " ")
            )
        details = {
            detail.find("small").text: detail.find("strong").text
            for detail in soup.find(attrs={"class": "about-items"}).children
            if len(detail) > 2
        }
        # Skip the <b></b> marks
        description = soup.find(attrs={"class": "text"}).text.replace("\xa0", " ")
        url = response.url
        if self.json_data.get(url) is None:
            self.json_data[url] = {
                "job_title": job_title,
                "offerer": offerer,
                "payment": payment,
                "details": details,
                "requirements": self._get_requirements(soup),
                "methodologies": self._get_methodologies(soup),
            }
        else:
            print(f"duplicate for url: {url}")

    def _get_requirements(self, soup):
        # Only the first two "tag-clouds" are about requirements
        requirements = soup.find_all(attrs={"class": "tag-clouds"})[:2]
        requirements = [
            [li.text.strip("\n") for li in r.find_all("li")] for r in requirements
        ]
        return {"must_have": requirements[0], "nice_to_have": requirements[1]}

    def _get_methodologies(self, soup):
        work_methodology = soup.find(attrs={"class": "features"}).find_all(
            attrs={"class": "list-group-item"}
        )
        methodologies = {}
        for wm in work_methodology:
            value = hasattr(wm, "attrs") and "checked" in wm.attrs["class"]
            if value:
                # place detailed methodology description if there is any
                value = wm.find(attrs={"class": "text-muted"})
                value = value.text.strip()[2:] if value is not None else True
            title = wm.text.strip()
            # Offers may have detail in text, we remove it since it's duplicate
            title = title.split("\n")[0] if "\n" in title else title
            methodologies[title] = value
        return methodologies
