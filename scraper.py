import re
from urllib.parse import urlparse, urljoin, urlunparse
from bs4 import BeautifulSoup
from collections import Counter
from collections import defaultdict
import nltk
from nltk.corpus import stopwords

nltk.download("stopwords")
stopwords = set(stopwords.words('english'))

#1.unique urls
unique_urls = set()

#2.longest page
longest_page = ""
longest_page_words = 0

#3.fifty common words
common_words = Counter()

#4.subdomains
subdomains = defaultdict(int)

already_visited = set()


def scraper(url, resp):
    links = extract_next_links(url, resp)

    with open("url_log.txt", "a") as f: #write down all valid urls scrapped
        f.write(f'{url}\n')
        for link in links:
            if is_valid(link):
                f.write(f'\t{link}\n')

    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content

    new_links = set()
    global unique_urls, longest_page, longest_page_words, common_words, subdomains

    #normalize the url by unfragmenting it, removing trailing /s, and removing www. (easier to compare)
    parsed = urlparse(url)
    parsed = parsed._replace(fragment="") #unfragment the url by parsing it to replace the fragments and then unparsing it
    parsed = parsed._replace(path = urlparse(url).path.rstrip("/")) #trailing / removed
    if parsed.netloc.lower().startswith("www."): #remove www.
            parsed_domain = parsed.netloc[4:]
            parsed = parsed._replace(netloc = parsed_domain)

    #unparsing the url! (it goes back to being a url)
    url = urlunparse(parsed)
    
    #if the page has an error or has no response, skip this page
    if resp.status != 200 or resp.raw_response is None:
        already_visited.add(url)
        return list(new_links)
    
    try:
        #parse through html
        soup = BeautifulSoup(resp.raw_response.content, "html.parser")

        #adding url's subdomain to global subdomains dict and then sorting it alphabetically and by decreasing
        subdomain_parts = parsed.netloc.split('.')
        subdomain = '.'.join(subdomain_parts[:-2])
        subdomains[subdomain] += 1
        sorted_subdomains = dict(sorted(subdomains.items(), key=lambda item:(-item[1],item[0])))

        #adding it to unique urls
        if url not in unique_urls:
            unique_urls.add(url)

        #getting all words on page (words is raw words, filtered_words is without stopwords)
        text = soup.get_text()
        words = re.findall(r"\b[a-zA-Z']+\b", text.lower())
        filtered_words = [word for word in words if word.lower() not in stopwords]

        #counting length of words to keep track of longest page
        word_count = len(words)
        if word_count > longest_page_words:
            longest_page_words = word_count
            longest_page = url

        #counting the frequency of of words
        word_frequencies = Counter(filtered_words)
        common_words += word_frequencies


        #magic happens: finds all hyperlinks, joins the hyperlinks, normalizes it, and adds it to list of new_links
        for hyperlink in soup.find_all("a", href = True): #loops through all hyperlinks
            hyperlink_url = hyperlink.get("href") #get the hyperlink's url (is an extension or a completely new domain)
            full_url = urljoin(url,hyperlink_url) #joins the hyperlink's url to the current domain (or returns hyperlink_url if it is a completely new domain)
            
            parsed_hyperlink = urlparse(full_url)
            parsed_hyperlink = parsed_hyperlink._replace(fragment="") #unfragment the url by parsing it to replace the fragments and then unparsing it
            parsed_hyperlink = parsed_hyperlink._replace(path = urlparse(full_url).path.rstrip("/")) #trailing / removed
            if parsed_hyperlink.netloc.lower().startswith("www."): #remove www.
                domain = parsed_hyperlink.netloc[4:]
                parsed_hyperlink = parsed_hyperlink._replace(netloc = domain)

            full_url = urlunparse(parsed_hyperlink)
            if full_url != url: #ensure the url is not the same one as it is currently on so we do not circle back
                new_links.add(full_url) #adds to list of links

        #logs everything for the report
        with open('report.txt', 'a') as f:
            f.write(f'Unique URLS: {len(unique_urls)}\n')
            f.write(f'Longest Page: {longest_page}\t{longest_page_words} words\n')
            f.write(f'Fifty Common Words: {common_words.most_common(50)}\n')
            f.write(f'Subdomains: {sorted_subdomains}\n\n')

        already_visited.add(url)
        return list(new_links)
    except Exception as e:
        print(f'Error extracting from {url}\nError: {e}')
        already_visited.add(url)
        return list(new_links)

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.

    try:
        parsed = urlparse(url)

        if url in already_visited:
            return False
        
        if parsed.scheme not in set(["http", "https"]): #if scheme not http or https
            return False
        
        allowed_domains = [
            "ics.uci.edu", 
            "cs.uci.edu", 
            "informatics.uci.edu",
            "stat.uci.edu", 
            "today.uci.edu/department/information_computer_sciences"
        ]

        domain = parsed.netloc.lower()
        if not any (domain == d or domain.endswith(f'.{d}') for d in allowed_domains): #if domain not in any of the allowed_domains for the assignment
            return False
        
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()) #checking the path

    except TypeError:
        print ("TypeError for ", parsed)
        raise
