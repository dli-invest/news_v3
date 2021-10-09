import scrapy
import re
from scrappers.get_tickers import TickerControllerV2

class YahooStockSpider(scrapy.Spider):
    name = "stock_news"
    base_yahoo_url = "https://ca.finance.yahoo.com/quote"
    ticker_controller = TickerControllerV2({})
    should_visit_news_articles = False

    def start_requests(self):
        tickers = self.ticker_controller.get_ytickers()
        yahoo_urls = [f"{self.base_yahoo_url}/{ticker}" for ticker in tickers]
        print(len(yahoo_urls))
        urls = yahoo_urls[0:1]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)
            

    def parse(self, response):
        try:
            url = response.url
            page_title = url.rsplit('/', 1)[1]
            page_title = page_title[:-4]
            page_title = page_title.replace("-", " ")
            page_title = re.sub(r"d+$", "", page_title)
            # rework this scrapping logic to only use BeautifulSoup
            full_soup = BeautifulSoup(response.body, features="lxml")
            article_items = soup.find_all("li", {"class": "js-stream-content"})
            # article_links = soup.find_all("a", {"class": "js-content-viewer"})
        timestamp = full_soup.find('time').text
        except Exception as e:
            pass
        for a_tag in response.css('a.js-content-viewer'):
            href = a_tag.attrib["href"]
            if href is not None:
                # ignore mailto and tel linkst
                if href[0:3] == "tel":
                    continue
                elif href[0:6] == "mailto":
                    continue
                
                if should_visit_news_articles == True:
                    href_merged = response.urljoin(href)
                    if href_merged not in self.read_article_urls:
                        yield scrapy.Request(href_merged, callback=self.handle_article, dont_filter=True)
                    else:
                        print("visited: " + href_merged)

    def handle_article(self, response):
        url = response.url
        page_title = url.rsplit('/', 1)[1]
        page_title = page_title[:-4]
        page_title = page_title.replace("-", " ")
        # rework this scrapping logic to only use BeautifulSoup
        full_soup = BeautifulSoup(response.body, features="lxml")
        timestamp = full_soup.find('time').text
        article_date = dateparser.parse(timestamp)
        current_date = datetime.now()
        body = response.css('div.caas-body-section div.caas-content div.caas-body').get()
        soup = BeautifulSoup(body, features="lxml")
        article_data = soup.text
        article_data.\
            replace("Story continues.", "").\
            replace("Download the Yahoo Finance app, available for Apple and Android.", "")
        
        doc = nlp(article_data)
        entities = []
        has_critical_term = False
        for ent in doc.ents:
            if ent.label_ == "CRITICAL":
                has_critical_term = True
            entities.append({
                "text": ent.text,
                "label": ent.label_
            })
        entities = [dict(t) for t in {tuple(d.items()) for d in entities}]
        diff_date = current_date - article_date
        # map entities to fields
        embeds = []
        fields = []
        data = {}
        if diff_date.seconds // 3600 < 24:
            # send article to discord
            # map data to embeds
            for ent in entities[:24]:
                fields.append({
                    "name": ent.get("text"),
                    "value": ent.get("label"),
                    "inline": True
                })
            first_sentence = article_data[:100]
            # MAP type to color
            embed = {
                # "color": color,
                "title": page_title,
                "timestamp": article_date.isoformat(),
                "url": url,
                "fields": fields,
                "description": first_sentence
            }
            embeds.append(embed)
            data["embeds"] = embeds
            self.post_webhook_content(data)
            self.read_article_urls.append(url)



    # @classmethod
    # def from_crawler(cls, crawler, *args, **kwargs):
    #     spider = super(ScraperForYahoo, cls).from_crawler(crawler, *args, **kwargs)
    #     crawler.signals.connect(spider.spider_opened, signals.spider_opened)
    #     crawler.signals.connect(spider.spider_closed, signals.spider_closed)
    #     return spider

    # def spider_opened(self, spider):
    #     print("spider opened")

    # def spider_closed(self, spider):
    #     clean_list = list( dict.fromkeys(self.read_article_urls) )
    #     if len(clean_list) > 0:
    #         with open(output_file, 'w') as txt_file:
    #             for article_url in clean_list:
    #                 txt_file.write(article_url +"\n")

    def post_webhook_content(self, data: dict):
        url = self.webhook

        result = requests.post(
            url, data=json.dumps(data), headers={"Content-Type": "application/json"}
        )

        try:
            result.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
        else:
            print("Payload delivered successfully, code {}.".format(result.status_code))