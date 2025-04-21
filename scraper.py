import re
from urllib.parse import urlparse, urljoin, urlunparse
from bs4 import BeautifulSoup

def scraper(url, resp):
    links = extract_next_links(url, resp)
    with open("url_log.txt", "a") as f:
        f.write(f'{url}\n')
        for link in links:
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

    frontier = set()

    #if the page has an error, skip this page
    if resp.status != 200 or resp.raw_response is None:
        return list(frontier)
    
    try:
        #parse through html
        soup = BeautifulSoup(resp.raw_response.content, "html.parser")
        for hyperlink in soup.find_all("a", href = True): #loops through all hyperlinks
            hyperlink_url = hyperlink.get("href") #get the hyperlink's url (is an extension or a completely new domain)
            full_url = urljoin(url,hyperlink_url) #joins the hyperlink's url to the current domain (or returns hyperlink_url if it is a completely new domain)
            full_url = urlunparse(urlparse(full_url)._replace(fragment="")) #unfragment the url by parsing it to replace the fragments and then unparsing it
            frontier.add(full_url) #adds to list of links

        return list(frontier)
    except Exception as e:
        print(f'Error extracting from {url}\nError: {e}')
        return list(frontier)

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        
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
        if not any (domain.endswith(d) for d in allowed_domains): #if domain not in any of the allowed_domains for the assignment
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
