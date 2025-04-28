import regex
import re
from urllib.parse import urlparse, urljoin, urlunparse
from bs4 import BeautifulSoup
from collections import Counter
from collections import defaultdict
import nltk
from nltk.corpus import stopwords

nltk.download("stopwords")
stopwords = set(stopwords.words('english'))

#*---------- GLOBAL VARIABLES ------------
# irrelevant words not included in search. naive approach to stopword selection.
# stopwords = [
#     "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at",
#     "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't", "cannot", "could",
#     "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
#     "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's",
#     "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
#     "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't",
#     "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
#     "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't",
#     "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
#     "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too",
#     "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't",
#     "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's",
#     "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
#     "yourselves"
# ]

# track all unique pages to visit and store in a set for future lookup
unique_urls = set()
already_visited = set() #already crawled
already_seen = set() #already seen
min_words = 80 #based on a website with no content just pictures -- the words count for the headings and dropdown menus
max_words = 30000 #arbitrary number to limit the number of words on a page

# record pages for report
longest_page = "" # includes stop words
longest_page_words = 0 # includes stop words
longest_page_filtered_words = 0 # excludes stop words
common_words = Counter() # track word frequencies
subdomains = defaultdict(int) # track subdomains in a dictionary

#*---------- SCRAPER INTERFACE ------------
def scraper(url, resp):
    # extract valid links from the page
    # writes to url_log.txt (tracker)
    # returns list of valid links
    links = extract_next_links(url, resp)

    with open("url_log.txt", "a") as f:
        f.write(f'{url}\n')
        for link in links:
            if is_valid(link):
                f.write(f'\t\t{link}\n')

    return [link for link in links if is_valid(link)]

#*---------- LINK EXTRACTION LOGIC ------------
def extract_next_links(url, resp):
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    try:
        #* ---------- PARSE PAGE CONTENT ------------
        new_links = set()
        global unique_urls, longest_page, longest_page_words, longest_page_filtered_words, common_words, subdomains

        #if the page has an error or has no response, skip this page
        if resp.status != 200 or resp.raw_response is None:
            already_visited.add(url)
            return list(new_links)
            
        #parse through html and extract words
        #\b: word boundary
        #\p{L}+: 1 or more unicode characters
        #(?:['’]\p{L}+)?: optional apostrophe with more unicode characters
        soup = BeautifulSoup(resp.raw_response.content, "html.parser")
        text = soup.get_text()
        words = regex.findall(r"\b\p{L}+(?:['’]\p{L}+)?\b", text.lower()) 

        # filter words
        words = [word for word in words if len(word) > 1] #ensure words are at least two characters
        filtered_words = [word for word in words if word.lower() not in stopwords] #filter out stopwords
        if len(filtered_words) < min_words or len(filtered_words) > max_words: # filter out low value info
            already_visited.add(url)
            return list(new_links)
        
        #* ---------- QUALITY CHECK, EXTRACT LINKS, NORMALIZE URL ------------
        # quality check.
        # only extract links if the page is high quality (based on instructions) - Jasmine
        quality = is_high_quality(soup, text, filtered_words)
        if quality:
            # Extract and normalize links 
            for hyperlink in soup.find_all("a", href = True):
                href = hyperlink.get("href")
                if href and not href.startswith('#'):
                    full_url = urljoin(url, href)
                    if is_valid(full_url):
                        # Normalize the URL (remove fragment, trailing /, and www.)
                        parsed = urlparse(full_url)
                        parsed = parsed._replace(fragment="") #unfragment the url by parsing it to replace the fragments and then unparsing it
                        parsed = parsed._replace(path = parsed.path.rstrip("/")) #use full_url instead of original url - Jasmine
                        if parsed.netloc.lower().startswith("www."): #remove www.
                            parsed_domain = parsed.netloc[4:]
                            parsed = parsed._replace(netloc = parsed_domain)
                        
                        #unparsing the url! (it goes back to being a url)
                        full_url = urlunparse(parsed)
                        
                        # Check for duplicates
                        if full_url != url and full_url not in already_seen:
                            already_seen.add(full_url)
                            new_links.add(full_url)

        #* ---------- LOG PAGE DETAILS ------------
        # adding it to unique urls
        unique_urls.add(url)

        # track longest page
        word_count = len(words)
        filtered_word_count = len(filtered_words)
        if word_count > longest_page_words:
            longest_page_words = word_count
            longest_page_filtered_words = filtered_word_count
            longest_page = url

        # count word frequencies
        word_frequencies = Counter(filtered_words)
        common_words += word_frequencies

        # add url's subdomain to global subdomains dict and then sorting it alphabetically and by decreasing
        # subdomain is valid if it has at least 2 parts (dots)
        subdomain = ""
        if len(parsed.netloc.split('.')) > 2:
            subdomain = '.'.join(parsed.netloc.split('.')[:-2])
        else:
            subdomain = parsed.netloc # if not a valid subdomain, use entire domain
        subdomains[subdomain] += 1
        sorted_subdomains = dict(sorted(subdomains.items(), key=lambda item:(-item[1],item[0])))
        already_visited.add(url)

        with open('report.txt', 'a') as f:
            f.write(f'Unique URLS: {len(unique_urls)}\n')
            f.write(f'URLS Seen: {len(already_visited)}\n')
            f.write(f'Longest Page: {longest_page}\t{longest_page_words} words\t{longest_page_filtered_words} words without stopwords\n')
            f.write(f'Fifty Common Words: {common_words.most_common(50)}\n')
            f.write(f'Subdomains: {sorted_subdomains}\n\n')

        return list(new_links)
    except Exception as e:
        print(f'Error extracting from {url}\nError: {e}')
        already_visited.add(url) 
        return list(new_links)

#*---------- URL VALIDATION ------------
def is_valid(url):
    # Decide whether to crawl this url or not.
    # Detect common traps
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.

    try:
        # define allowed and unallowed domains (low value or traps)
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        allowed_domains = [
            "ics.uci.edu", 
            "cs.uci.edu", 
            "informatics.uci.edu",
            "stat.uci.edu", 
            "today.uci.edu"
        ]
        unallowed_paths = [
            "/admin", #administrator info
            "/auth/", #no value - account login
            "/videos/", #leads to videos
            "/image", #leads to images
            "/attachment/", #leads to file/image
            "-attachment/", #leads to files
            "/img_", #leads to image
            "/photo", #leads to image
            "/files/", #leads to files
            "/-/", #git commands/logs
            "/calendar/", #calendars
        ]
        unallowed_queries = [
            "ical=1",
            "filter",
            "action",
            "rev",
            "do",
            "sessionid",
            "token",
            "preview=true",
            "printable=yes",
            "keywords",
            "search"
        ] + ["share", "utm_source", "utm_medium", "utm_campaign", "ref", "fbclid", "gclid"]
        # added social sharing keywords as traps; from Claude 3.7 Sonnet -JD

        #* ---------- TRAPS ------------
        #if already visited
        if url in already_visited:
            return False
        #if scheme not http or https
        if parsed.scheme not in set(["http", "https"]):
            return False
        # if domain is not allowed
        if not any (domain == d or domain.endswith(f'.{d}') for d in allowed_domains):
            return False
        # specific domain edge case
        if domain == "today.uci.edu" and not parsed.path.startswith("/department/information_computer_sciences"):
            return False
        #if path is not allowed
        if any(p in parsed.path.lower() for p in unallowed_paths):
            return False
        # if query is not allowed
        if any(parsed.query.lower() == q or parsed.query.lower().startswith(q) for q in unallowed_queries):
            return False
        if "rev" and "do" in parsed.query.lower():
            return False
        # if path is a calendar
        if '/events/' in parsed.path.lower():
            if any([
                re.search(r"/\d{4}-\d{2}-\d{2}", parsed.path.lower()),
                re.search(r"/\d{4}-\d{2}", parsed.path.lower()),
                re.search(r"/\d{4}/\d{2}", parsed.path.lower()),
                re.search(r"month", parsed.path.lower()),
                re.search(r"list", parsed.path.lower()),
                re.search(r"today", parsed.path.lower())
                ]):
                return False
        # Jasmine - large search query traps (ex: ?filter=1&filter=2&filter=3)
        if len(parsed.query.split('&')) > 3:
            return False
        # if file extension is not allowed
        return not (
            re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz"
            + r"|java|py|sql|c|apk|odc|img|mpg|grm|frk|bam|git|lif|ff|war|webp|rkt|rle|bundle|diff|isp|lsp|nb|m|nz|z)$", parsed.path.lower())
        )

    except TypeError:
        print ("TypeError for ", parsed)
        raise

#*---------- CONTENT CHECK ------------
def is_high_quality(soup, text, filtered_words):
    # text-to-html ratio
    html_size = len(str(soup))
    text_size = len(text)
    ratio = text_size / html_size if html_size > 0 else 0

    # check content organization
    has_headings = len(soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])) > 0
    has_paragraphs = len(soup.find_all("p")) > 0  # Relaxed from > 2
    
    # Relaxed criteria - Jasmine
    # 0.01 ensures at least 1% of the page is text
    # must have headings and paragraphs
    return ratio > 0.01 and has_headings and has_paragraphs

