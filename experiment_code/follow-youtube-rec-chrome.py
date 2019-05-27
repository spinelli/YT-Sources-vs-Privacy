# running example: 
# python2.7 follow-youtube-rec-firefox.py  --query="DACA" --searches=1 --branch=1 --depth=21 --name="test" --order=0 --security=3


# Code initially devellope by Guillaume Chaslot
# addapted and extended by Larissa Spinelli
__author__ = 'Guillaume Chaslot and Larissa Spinelli'


"""
    This scripts starts from a search query on youtube and:
        1) gets the N first search results
        2) follows the first M recommendations
        3) repeats step (2) P times
        4) stores the results in a json/csv file
"""

import urllib2
import re
import json
import sys
import argparse
import time


from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
from bs4 import BeautifulSoup
import string
import sys
import random
import re
import socket
import urllib
import os

from graphviz import Digraph

import pandas as pd

TIMESLEEP = 6

RECOMMENDATIONS_PER_VIDEO = 1
RESULTS_PER_SEARCH = 1

# NUMBER OF MIN LIKES ON A VIDEO TO COMPUTE A LIKE RATIO
MIN_LIKES_FOR_LIKE_RATIO = 5

class YoutubeFollower():
	 # just initialize the follower code
    def __init__(self, verbose=False, name='', alltime=True, gl=None, language=None, recent=False, loopok=True, trending=False, sequence=0):
        # Name
        self._name = name
        self._alltime = alltime
        self._verbose = verbose
        self._video_infos = {} # self.try_to_load_video_infos()
        self._video_infosExt = {} # self.try_to_load_video_infos()
        self._initial_trend = []
        self._final_trend = []
        
        # Dict search terms to [video_ids]
        self._search_infos = {}
        self._gl = gl
        self._language = language
        self._recent=recent
        self._loopok=loopok
        self._trending=trending
        self._sequence=sequence
        self._driver= []
        self._order = 1
        self._search_terms = ""

        print ('Location = ' + repr(self._gl) + ' Language = ' + repr(self._language))

    def clean_count(self, text_count):
        # Ignore non ascii
        ascii_count = text_count.encode('ascii', 'ignore')
        # Ignore non numbers
        p = re.compile('[\d,]+')
        return int(p.findall(ascii_count)[0].replace(',', ''))

	 # open research youtube page and return the link for the x-first files
    def get_search_results(self, search_terms, max_results, browser, top_rated=False):
        assert max_results < 20, 'max_results was not implemented to be > 20'
        
        if self._verbose:
            print ('Searching for {}'.format(search_terms))

        # Trying to get results from cache
        if search_terms in self._search_infos and len(self._search_infos[search_terms]) >= max_results:
            return self._search_infos[search_terms][0:max_results]

        # Escaping search terms for youtube
        escaped_search_terms = urllib2.quote(search_terms.encode('utf-8'))
        self._search_terms = escaped_search_terms

        # We only want search results that are videos, filtered by viewcoung.
        #  This is achieved by using the youtube URI parameter: sp=CAMSAhAB
        if self._alltime:
            filter = "CAMSAhAB"
        else:
            if top_rated:
                filter = "CAE%253D"
            else:
                filter = "EgIQAQ%253D%253D"

        url = "https://www.youtube.com/results?sp=" + filter + "&q=" + escaped_search_terms
        if self._gl:
            url = url + '&gl=' + self._gl

        headers = {}
        if self._language:
            headers["Accept-Language"] = self._language
        
        print ('Searching URL: ' + url)    
        browser.get(url)
        time.sleep(random.randint(1,TIMESLEEP))
        html_source = browser.page_source.encode('utf-8')
        soup = BeautifulSoup(html_source, "lxml")
        
        # get list of videos from search
        videos = []
        for item_section in soup.findAll('div', {'class': 'text-wrapper style-scope ytd-video-renderer'}):
            links = item_section.findAll('a', href= True)
            for link in links:
                if len(link['href'].split('=')) > 1:
                    link_vid = link['href'].split('=')[1]
                    videos.append(link_vid)

        # video selection [1: random; -1: bottom item; 0: top item]
        self._search_infos[search_terms] = videos
        if len(videos) > 1:
        	count = 0
        	if self._sequence == 1:
        		vid = random.choice(videos)
        		while vid in self._video_infos and count < 10:
        			count = count + 1
        			vid = random.choice(videos)
        		vids = [vid]
        	elif self._sequence == -1:
        		vid = videos[-1]
        		while vid in self._video_infos and count < 10:
        			count = count + 1
        			vid = videos[-1-count]
        		vids = [vid]
        	elif self._sequence == 0:
        		vid = videos[0]
        		while vid in self._video_infos and count < 10:
        			count = count + 1
        			vid = videos[0+count]
        		vids = [vid]	
        	else:		
        		vids = videos[0:max_results]
        else:
        	vids = videos[0:max_results]
	
        print "videos"
        print vids
        return vids		

    def get_recommendations(self, video_id, nb_recos_wanted, depth, key, browser, order=1):
        if video_id in self._video_infos:
            # Updating the depth if this video was seen.
            self._video_infos[video_id]['depth'] = min(self._video_infos[video_id]['depth'], depth)
            print ('a video was seen at a lower depth')

            
            video = self._video_infos[video_id]
            
            video['order'].append(self._order)    
            self._order = self._order + 1
            
            print video['recommendations']
            recos_returned = []
            for reco in video['recommendations']:
                # This line avoids to loop around the same videos:
                if reco not in self._video_infos or self._loopok:
                    recos_returned.append(reco)
                    if len(recos_returned) >= nb_recos_wanted:
                        break
            if self._loopok:
                video['key'].append(key)
            print ('\n Following recommendations ' + repr(recos_returned) + '\n')
            return recos_returned

        url = "https://www.youtube.com/watch?v=" + video_id

        browser.get(url)
        time.sleep(random.randint(4,TIMESLEEP*2))
        # Waiting for adds
        adds = False
        try:
            if browser.find_element_by_css_selector('.videoAdUiPreSkipText'):
                print "Add is running - please wait"
                adds = True
                time.sleep(random.randint(TIMESLEEP,TIMESLEEP*2))
        except:
            pass
        
          
        try:
            browser.find_element_by_css_selector('.videoAdUiSkipButton').click()
            print "skipped add"
            adds = True
            time.sleep(1)
        except:
            pass
           
       
        # Stop video
        try:
            browser.find_element_by_css_selector('.ytp-play-button.ytp-button').click()
            time.sleep(1)
            browser.find_element_by_css_selector('.ytp-play-button.ytp-button').click()
        except:
            time.sleep(8)
            pass
            
        
        html_source = browser.page_source.encode('utf-8')
        soup = BeautifulSoup(html_source, "lxml")
        
               # YT clarification
       	print "clarification notes" 
        clarification = 0
        clar_notes = ""
        clar_link = ""
        try:
		     if soup.find('div', {'id': 'clarify-box'}):
			print "found"
		        clarification = 1
		        clar_notes = soup.find('div', {'id': 'clarify-box'})
		        for item_section in clar_notes.findAll('a'):
		        	clar_link = item_section['href']
		        	break
		       
	except:
		pass
            
        print clarification
        print clar_link 
        
        
        
           
         # Channel
        channel = ''
        channel_id = ''
        for item_section in soup.findAll('a', {'class': 'yt-simple-endpoint style-scope yt-formatted-string'}):
            if item_section['href'] and ('/channel/' in item_section['href']) and item_section.contents[0] != '\n':
                channel = item_section.text
                channel_id = item_section['href'].split('/channel/')[1]
                break
                
    
        if channel == '':
            outname = "nochannel.html"
            file0 = open(outname,"w") 
            file0.write(str(soup))
            print ('WARNING: CHANNEL not found')
            time.sleep(8)
            html_source = browser.page_source.encode('utf-8')
            soup = BeautifulSoup(html_source, "lxml")
        else:
            outname = "withchannel.html"
            file0 = open(outname,"w") 
            file0.write(str(soup))
          
   
     
        verified=""
        datePub = "none"
        if soup.find('span', {'slot': 'date'}):
            datePub = soup.find('span', {'slot': 'date'}).text    
            
        tmpDs = soup.findAll('div', {'id': 'owner-container'})
        for tmpD in tmpDs:
            
            
            
            tmps = tmpD.findAll('div', {'id': 'tooltip'})
            for tmp in tmps:
                #print tmp.text
                verified = str(tmp.text).strip()
                #print verified
        
         
             
        
        
         
            
            
        # Views
        views = -1
        for watch_count in soup.findAll('span', {'class': 'view-count style-scope yt-view-count-renderer'}):
            try:
                views = self.clean_count(watch_count.contents[0])
            except IndexError:
                pass
        # Likes and dislikes
        likes = -1
        dislikes = -1
        
        for like_count in soup.findAll('yt-formatted-string', {'class': 'style-scope ytd-toggle-button-renderer style-text'}):
            try:
                if "aria-label" in str(like_count):
                    #print like_count
                    if "dislike" in like_count['aria-label']:
                        #print like_count
                        dislikes = self.clean_count(like_count['aria-label'])
                        #print dislikes
                    else:    
                        #print like_count
                        likes = self.clean_count(like_count['aria-label'])
                        #print likes
                
            except IndexError:
                #print like_count
                pass
        
             
       
            
            
        # Subscribers
        subscribers = -1
        
        for like_count in soup.findAll('span', {'class': 'deemphasize style-scope yt-formatted-string'}):
            try:
                subscribers = self.clean_count(like_count.text)
            except IndexError:
                pass 
        #print subscribers
        
      
            
            
        # Recommendations
        
        recos = []
        if depth > 0:
            upnext = True
            for video_list in soup.findAll('a', {'class': 'yt-simple-endpoint style-scope ytd-compact-video-renderer'}):
            #print video_list
                if not "href" in str(video_list):
                    upnext = False
                else:
                    upnext = True
                if upnext:
                    # Up Next recommendation
                    try:
                        recos.append(str(video_list['href'].replace('/watch?v=', '')))
                    
                    except IndexError:
                        print ('WARNING Could not get a up next recommendation because of malformed content')
                        pass
                
        print "recos " + str(recos)   

        title = ''
        for eow_title in soup.findAll('a', {'data-sessionlink': 'feature=player-title'}):
            title = eow_title.text.strip()

        if title == '':
            print ('WARNING: title not found')

        #video lenght    
        timeWait = 10
        lenght = 1
        try:
            tim = soup.find('span', {'class': 'ytp-time-duration'})
           
            
            timeWait, lenght = timeVideo(tim.text)
            
        except:
            pass
        
        
        
         # Try to see "more info about the video"
        try:
            browser.find_element_by_css_selector('.more-button.style-scope.ytd-video-secondary-info-renderer').click()
            html_source = browser.page_source.encode('utf-8')
            soup = BeautifulSoup(html_source, "lxml")
            print "see more info"
        except:
            print "no click on see more info"
            pass
        
         
        # Description
        description = "none"
        
        try:
            description = soup.find('yt-formatted-string', {'class': 'content style-scope ytd-video-secondary-info-renderer'}).text
            #print description
            
        except:
            pass 
        
           
        # Category
        category = "none"
        license = "none"
        #print "category and licence"
        try:
            #print soup.findAll('ytd-metadata-row-renderer')
            #print soup.findAll('yt-formatted-string', {'class': 'content content-line-height-override style-scope ytd-metadata-row-renderer'})
            count = 1
            tmps = soup.findAll('yt-formatted-string', {'class': 'content content-line-height-override style-scope ytd-metadata-row-renderer'})
            for tmp in tmps:
                #print count
                #print tmp.text
                if count == len(tmps)-1:
                    category = tmp.text
                elif count == len(tmps):
                    license = tmp.text     
                count = count + 1
                
           
            try:
                if channel == '' and channel_id == '':
                    #print "trying to get channel name"
                    for item_section in soup.findAll('a', {'class': 'yt-simple-endpoint style-scope yt-formatted-string'}):
                        if item_section['href'] and ('/channel/' in item_section['href']) and item_section.contents[0] != '\n':
                            channel = item_section.text
                            channel_id = item_section['href'].split('/channel/')[1]
                            break
            except:
                pass
        except:
            pass    
            
       
        # Comments
        comments = ""
        
        try:
            # "scroll down to get comments"
            actions = ActionChains(browser)
            for _ in range(3):
                actions.send_keys(Keys.PAGE_DOWN).perform()
                time.sleep(1)
            actions.send_keys(Keys.ENTER).perform()
            #actions.move_by_offset(1,1).perform()    
            time.sleep(5)
            #print  "scroll"
            html_source = browser.page_source.encode('utf-8')
            soup = BeautifulSoup(html_source, "lxml")
            for comment in soup.findAll('yt-formatted-string', {'class': 'count-text style-scope ytd-comments-header-renderer'}):
                if "Comments" in comment.text:
                    comments = comment.text
                
        except:
            pass 
        #print "comments " + comments
    
    	print recos
    	if len(recos) > 1:
    		if self._sequence == 1:
        		vid = random.choice(recos)
        		while vid in self._video_infos and count < 20:
        			count = count + 1
        			vid = random.choice(recos)
        		recs = [vid]
        	elif self._sequence == -1:
        		vid = recos[-1]
        		while vid in self._video_infos and count < 10:
        			count = count + 1
        			vid = recos[-1-count]
        		recs = [vid]
        	elif self._sequence == 0:
        		vid = recos[0]
        		while vid in self._video_infos and count < 10:
        			count = count + 1
        			vid = recos[0+count]
        		recs = [vid]	
        	else:		
        		recs = recos[:nb_recos_wanted]
	else:
		recs = recos  			
  	
	print "recs:"
	print recs
        print "going to save file"
	date = time.strftime('%Y-%m-%d')

        if video_id not in self._video_infos:
        	
		self._video_infos[video_id] = {'views': str(views),
                                           'likes': int(likes),
                                           'dislikes': int(dislikes),
                                           'recommendations': recs,
                                           'title': title,
                                           'depth': depth,
                                           'id': video_id,
                                           'channel': (channel).encode('utf8').strip(),
                                           'channel_id': (channel_id).encode('utf8').strip(),
                                           'subscribers': subscribers,
                                           'datePublish': (datePub).encode('utf8').strip(),
                                           'lenght': lenght, 
                                           'category': category,
                                           'license': license,
                                           'verified': verified, 
                                           'key': [],
                                           'order' : [],
                                           'clarify': clarification,
                                           'clar_link': clar_link,
                                           'rec_qt' : 0}
      		print "going to save file2"          
		if self._loopok:
			self._video_infos[video_id]['key'].append(key)
		self._video_infos[video_id]['rec_qt'] = self._video_infos[video_id]['rec_qt'] + 1
        	self._video_infos[video_id]['order'].append(self._order) 
        	self._order = self._order + 1
        
        print "saving extend file"
        videos = {}
	videos[self._order] = self._video_infos[video_id]
	#print videos 	
        dataL = pd.DataFrame.from_dict(videos, orient='index')
        print "checking"
        print dataL
        outfile03 = 'data-' + self._name + '_'  + date + "_" +  self._search_terms + '.csv'
        #outfile03 = 'dataTemp.csv'
        print outfile03
        if not os.path.isfile(outfile03):
        	dataL.to_csv(outfile03, header='column_names', sep=';')
        else:
        	dataL.to_csv(outfile03, mode='a', header=False, sep=';') 
    
    		print "done"
        try:
        	if video_id not in self._video_infosExt:
            		self._video_infosExt[video_id] = {'recos': recos,
                                           'adds': adds,
                                           'id': (video_id).encode('utf8').strip(),
                                           'description': description.encode('utf8').strip(),
                                           'comments': comments.encode('utf8').strip(),
                                           'trend': False}
		if video_id in self._initial_trend:
                	self._video_infosExt[video_id]['trend'] = True
      		videos[self._order] = self._video_infosExt[video_id]
		#print videos 	
        	dataL = pd.DataFrame.from_dict(videos, orient='index')
        	print "checking 2"
        	#print dataL
        	outfile03 = 'dataExt-' + self._name + '_'  + date + "_" + self._search_terms + '.csv'
        	#outfile03 = 'dataTemp.csv'
        	if not os.path.isfile(outfile03):
        		dataL.to_csv(outfile03, header='column_names', sep=';')
        	else:
        		dataL.to_csv(outfile03, mode='a', header=False, sep=';') 
    
	except:
		pass      
        print "saving tmp file"
        video_info = self._video_infos
        
       



        video = self._video_infos[video_id]
        try:
		print ('## ' + repr(video_id + ': ' + str(video['title']) + ' [' + str(video['channel_id'])  + str(video['verified']) + ']{' + repr(key) +'} ' + str(video['views']) + ' views , depth: ' + str(video['depth'])))
        except:
		print ('## ' + repr(video_id + ': title_non_ascii [' + str(video['channel_id']) + ' ' + str(video['verified']) + ']{' + repr(key) +'} ' + str(video['views']) + ' views , depth: ' + str(video['depth'])))
        	pass
	#print (repr(video['recommendations']))
        print ('# ' +str(recos[:nb_recos_wanted]))
        
        print "Execute video for " +  str(timeWait)
        time.sleep(timeWait-10)
        
       	return recs
        
    def get_n_recommendations(self, seed, branching, depth, key, driver):
        if depth is 0:
            self.get_recommendations(seed, branching, depth, key,  driver)
            return [seed]
        current_video = seed
        all_recos = [seed]
        index = 0
        for video in self.get_recommendations(current_video, branching, depth, key,  driver):
            code = chr(index + 97)
            all_recos.extend(self.get_n_recommendations(video, branching, depth - 1, key + code, driver))
            index = index + 1
        return all_recos

    def compute_all_recommendations_from_search(self, driver, search_terms, search_results, branching, depth):
        if self._trending:
            search_results = self.get_trending(search_results, driver)
        else:
            search_results = self.get_search_results(search_terms, search_results, driver)
        print ('Search results ' + repr(search_results))

        all_recos = []
        ind = 0
        for video in search_results:
            ind += 1
            all_recos.extend(self.get_n_recommendations(video, branching, depth, str(ind), driver))
            print ('\n\n\nNext search: ')
        all_recos.extend(search_results)
        return all_recos

    def count(self, iterator):
        counts = {}
        for video in iterator:
            counts[video] = counts.get(video, 0) + 1
        return counts

    
    
    def go_deeper_from(self, driver, search_term, search_results, branching, depth):
        all_recos = self.compute_all_recommendations_from_search(driver,search_term, search_results, branching, depth)
        counts = self.count(all_recos)
        print ('\n\n\nSearch term = ' + search_term + '\n')
        print ('counts: ' + repr(counts))
        sorted_videos = sorted(counts, key=counts.get, reverse=True)
        return sorted_videos, counts

    def save_video_infos(self, keyword):
        print ('Wrote file:')
        date = time.strftime('%Y%m%d')
        with open('data/video-infos-' + keyword + '-' + date + '-' + order + '-' + name  + '.json', 'w') as fp:
            json.dump(self._video_infos, fp)

    def try_to_load_video_infos(self):
        try:
            with open('data/video-infos-' + keyword + '-' + date + '-' + order + '-' + name  + '.json', 'r') as fp:
                return json.load(fp)
        except Exception as e:
            print ('Failed to load from graph ' + repr(e))
            return {}

    def count_recommendation_links(self):
        counts = {}
        for video_id in self._video_infos:
            for reco in self._video_infos[video_id]['recommendations']:
                counts[reco] = counts.get(reco, 0) + 1
        return counts

    def like_ratio_is_computed(self, video):
        return int(video['likes']) > MIN_LIKES_FOR_LIKE_RATIO

    def print_graph(self, links_per_video, only_mature_videos=True):
        """
            Prints a file with a graph containing all videos.
        """
        input_links_counts = self.count_recommendation_links()
        graph = {}
        nodes = []
        links = []
        for video_id in self._video_infos:
            video = self._video_infos[video_id]
            if self.like_ratio_is_computed(video):
                popularity = 0
            else:
                popularity = video['likes'] / float(video['likes'] + video['dislikes'] + 1)

            nodes.append({'id': video_id, 'size': input_links_counts.get(video_id, 0), 'popularity': popularity, 'type': 'circle', 'likes': video['likes'], 'dislikes': video['dislikes'], 'views': video['views'], 'depth': video['depth']})
            link = 0
            for reco in self._video_infos[video_id]['recommendations']:
                if reco in self._video_infos:
                    links.append({'source': video_id, 'target': reco, 'value': 1})
                    link += 1
                    if link >= links_per_video:
                        break
        graph['nodes'] = nodes
        graph['links'] = links
        with open('./graph-' + self._name +  '.json', 'w') as fp:
            json.dump(graph, fp)
        date = time.strftime('%Y-%m-%d')
        with open('./graph-' + self._name +  '-' + date + '.json', 'w') as fp:
            json.dump(graph, fp)
        print ('Wrote graph as: ' + './graph-' + self._name +   '-' + date + '.json')

    def print_tree(self, links_per_video, only_mature_videos=True):
        """
            Prints a file with a graph containing all videos.
        """
        input_links_counts = self.count_recommendation_links()
        date = time.strftime('%Y-%m-%d')
        graphFile = 'diGraph-' + self._name + '_' +  date + '.gv'
        g = Digraph('G', filename=graphFile)
        graph = {}
        nodes = []
        links = []
        for video_id in self._video_infos:
            video = self._video_infos[video_id]
            if self.like_ratio_is_computed(video):
                popularity = 0
            else:
                popularity = video['likes'] / float(video['likes'] + video['dislikes'] + 1)

            nodes.append({'id': video_id, 'size': input_links_counts.get(video_id, 0), 'popularity': popularity, 'type': 'circle', 'likes': video['likes'], 'dislikes': video['dislikes'], 'views': video['views'], 'depth': video['depth']})
            link = 0
            recCount = 0
            labelNode = str(video['order']) + ":" + str(video_id) + " [" + video['channel'] + " "+ str(video['subscribers']) + "] " + str(video['likes']) + "/" + str(video['dislikes'])+ "/" + str(video['views']) 
            
            print labelNode
            
            if (video_id in self._initial_trend) or (video_id in self._final_trend):
                self._video_infos[video_id]['trend'] = True
                if self._video_infos[video_id]['adds']:
                    g.node(video_id, color='palegreen', style='filled', label=labelNode)
                else:
                    g.node(video_id, color='lightblue', style='filled', label=labelNode)
            else :
                if self._video_infos[video_id]['adds']:
                    g.node(video_id, color='lightyellow', style='filled', label=labelNode)
                else:
                    g.node(video_id, label=labelNode)
                
            for reco in self._video_infos[video_id]['recommendations']:
                if recCount < links_per_video:
                    g.edge(video_id, reco)
                recCount = recCount + 1    
                if reco in self._video_infos:
                    links.append({'source': video_id, 'target': reco, 'value': 1})
                    link += 1
                    if link >= links_per_video:
                        break
        graph['nodes'] = nodes
        graph['links'] = links
        
        dataPD = pd.DataFrame.from_dict(self._video_infos, orient='index')
        types = dataPD.apply(lambda x: pd.lib.infer_dtype(x.values))
        for col in types[types=='unicode'].index:
            dataPD[col] = dataPD[col].apply(lambda x: x.encode('utf-8').strip())
        print dataPD.head()
        outfile3 = 'results/data-' + self._name + '_'  + date + '.csv'
        print outfile3
    
        
        dataPD.to_csv(outfile3, index=False, sep=';', encoding='utf-8')
        
        g.view()
        with open('./graph-' + self._name + '_' +  '.json', 'w') as fp:
            json.dump(graph, fp)
        date = time.strftime('%Y-%m-%d')
        with open('./graph-' + self._name + '_'  + date + '.json', 'w') as fp:
            json.dump(graph, fp)
        print ('Wrote graph as: ' + './graph-' + self._name +  '-' + date + '.json')    

    def print_videos(self, videos, counts, max_length):
        totalV = 0
        for video in videos:
            try:
                totalV = totalV + counts[video]
            except KeyError:
                pass
        if totalV == 0:
              totalV = 1  
        idx = 1
        for video in videos[:max_length]:
            try:
                current_title = self._video_infos[video]['title']
                print (str(idx) + ') Recommended ' + str(counts[video]) + ' times ' + str(counts[video]) + '/' + str(totalV) + ' ' +  repr(float(counts[video])/float(totalV)) + ': ' + ' https://www.youtube.com/watch?v=' + video + ' , Title: ' + repr(current_title))
                if idx % 20 == 0:
                    print ('')
                idx += 1
            except KeyError:
                pass

    def get_top_videos(self, videos, counts, max_length_count):
        video_infos = []
        for video in videos:
            try:
                video_infos.append(self._video_infos[video])
                video_infos[-1]['nb_recommendations'] = counts[video]
            except KeyError:
                pass

        # Computing the average recommendations of the video:
        # The average is computing only on the top videos, so it is an underestimation of the actual average.
        if video_infos is []:
            return []
        sum_recos = 0
        for video in video_infos:
            sum_recos += video['nb_recommendations']
        if len(video_infos) > 0:
		avg = sum_recos / float(len(video_infos))
	else:
		avg = sum_recos
        for video in video_infos:
            video['mult'] = video['nb_recommendations'] / avg
        return video_infos[:max_length_count]

    def get_trending(self, max_results, browser):
        browser.get("https://youtube.com/feed/trending")
        time.sleep(random.randint(1,4))
        html_source = browser.page_source.encode('utf-8')
        soup = BeautifulSoup(html_source, "lxml")


        videos = []
        for item_section in soup.findAll('div', {'class': 'text-wrapper style-scope ytd-video-renderer'}):
                links = item_section.findAll('a', href= True)
                for link in links:

                    if len(link['href'].split('=')) > 1:
                        link_vid = link['href'].split('=')[1]
                        #print link_vid

                        videos.append(link_vid)
        return videos[0:max_results] 

def timeVideo(str_time, MAXT=300):
    #print str_time
    total = 0
    base = 1
    tims = str_time.split(':')
    #print tims
    for i in range(1, len(tims)+1):
        #print i
        #print tims[len(tims)-i]
        total = total + base*int(tims[len(tims)-i])
        base = base*60
    
    if total > MAXT:
        return MAXT, total
    else:
        return total, total
         
def compare_keywords(driver, query, search_results, branching, depth, name, gl, language, recent, loopok, trending, sequence):
    
    date = time.strftime('%Y-%m-%d')
    
    top_videos = {}
    name2 = name
    for keyword in query.split(','):
        name2 = name + "-" + keyword
        print name2
        yf = YoutubeFollower(verbose=True, name=name2, alltime=False, gl=gl, language=language, recent=recent, loopok=loopok, trending=trending, sequence=sequence)
        print "### Get initial trending videos" 
        #profile2 = webdriver.FirefoxProfile()
        #profile2.set_preference("browser.privatebrowsing.autostart", True)
        #profile2.set_preference("intl.accept_languages","en");
        #browser2 = webdriver.Firefox(profile2)
        #yf._initial_trend = yf.get_trending(20, browser2)
        #browser2.close()
        
        #print yf._initial_trend
        
        top_recommended, counts = yf.go_deeper_from(driver, keyword,
                          search_results=search_results,
                          branching=branching,
                          depth=depth)
        top_videos[keyword] = yf.get_top_videos(top_recommended, counts, 1000)
        yf.print_videos(top_recommended, counts, 100)
        yf.save_video_infos(name + '-' + keyword)
        #yf.print_graph(10)
        
        
        #print "### Get final trending videos" 
        #browser2 = webdriver.Firefox(profile2)
        #yf._final_trend = yf.get_trending(20, browser2)
        #browser2.close()
        #print yf._final_trend
        
        sizeT = max(branching, search_results)
        #yf.print_tree(sizeT)
        
        #print yf._video_infos
        
    file_name = 'resultsc/' + name2 + '-' + date + '-' + order + '.json'
    print ('Running, will save the resulting json to:' + file_name)    
    with open(file_name, 'w') as fp:
        json.dump(top_videos, fp)

def browser_urls(browser, urlsFile):
    f1 = open(urlsFile,"r")
    for url in f1:
        print url
        browser.get(url)
        time.sleep(random.randint(1,TIMESLEEP))
        #html_source = browser.page_source.encode('utf-8')
        #soup = BeautifulSoup(html_source, "lxml")
        
        # Subscribe 
        #try:
        #    browser.find_element_by_css_selector('.style-scope.ytd-button-renderer.style-destructive').click()
        #    time.sleep(random.randint(0,TIMESLEEP))
        #except IndexError:
        #    pass 


def random_line(fname):
    lines = open(fname).read().splitlines()
    line = random.choice(lines).split(',')
    return line[1]

def view_searching(browser, searchFile, top_t=5):
	f1 = open(searchFile,"r")
	searches = []
	while len(searches) < 6:
		search = random_line(searchFile)
		if search not in searches:
			#print search
			searches.append(search)
		#print len(searches)
	
	for terms in searches:
        	escaped_search_terms = urllib2.quote(terms.encode('utf-8'))

        

        	# We only want search results that are videos, filtered by viewcoung.
        	#  This is achieved by using the youtube URI parameter: sp=CAMSAhAB
        	filter = "CAMSAhAB"
        	
        	url = "https://www.youtube.com/results?sp=" + filter + "&q=" + escaped_search_terms
        
        	print ('Searching URL: ' + url)    
        	browser.get(url)
        	time.sleep(random.randint(1,TIMESLEEP))
        


        
def view_trending(browser,top_t=5):
    browser.get("https://youtube.com/feed/trending")
    time.sleep(random.randint(1,4))
    html_source = browser.page_source.encode('utf-8')
    soup = BeautifulSoup(html_source, "lxml")
    
    
    videos = []
    for item_section in soup.findAll('div', {'class': 'text-wrapper style-scope ytd-video-renderer'}):
            links = item_section.findAll('a', href= True)
            for link in links:
                
                if len(link['href'].split('=')) > 1:
                    link_vid = link['href'].split('=')[1]
                    #print link_vid
                
                    videos.append(link_vid)       
            
        
    for video in videos[:top_t]:
        try:
            url = 'https://www.youtube.com/watch?v=' + video 
            print url
            browser.get(url)
            time.sleep(random.randint(1,TIMESLEEP))
        except KeyError:
            pass  
        

        
def explore_trending(browser,top_t=5):
    browser.get("https://youtube.com/feed/trending")
    time.sleep(random.randint(1,4))
    html_source = browser.page_source.encode('utf-8')
    soup = BeautifulSoup(html_source, "lxml")
    
    
    videos = []
    for item_section in soup.findAll('div', {'class': 'text-wrapper style-scope ytd-video-renderer'}):
            links = item_section.findAll('a', href= True)
            for link in links:
                
                if len(link['href'].split('=')) > 1:
                    link_vid = link['href'].split('=')[1]
                
                    videos.append(link_vid)       
            
    all_recos = []
    ind = 0   
    for video in videos[:top_t]:
        ind += 1
        all_recos.extend(self.get_n_recommendations(video, branching, depth, str(ind), driver))
        print ('\n\n\nNext video: ')
        all_recos.extend(search_results)
        return all_recos   

def skipADD2(driver):
    time.sleep(random.randint(2,4))
    print("**********Printing Information In The begining ++++++++++++++++++++++");
    
    try:

        #videoAdUiPreSkipButton = driver.find(By.xpath("//div[@class='videoAdUiPreSkipButton']"));
        #print videoAdUiPreSkipButton
        videoAdUiPreSkipButton = soup.find('div', {'class': re.compile('videoAdUiPreSkipButton')})  
        print videoAdUiPreSkipButton
        
        print("*************VISIBILITY OF THE ELEMENT IS ************************* "
                + videoAdUiPreSkipButton.isDisplayed());


        if (videoAdUiPreSkipButton.isDisplayed() == true):
            print("*************Getting Text from the Pre text Box in the begining************************* " + videoAdUiPreSkipButton.getText());

            videoAdUiPreSkipButtonFirstDiv = driver.findElement(By.xpath("//div[@class='videoAdUiPreSkipButton']//div[1]"));
            print("*************Getting Text from the FIRST DIV in the begining*************************** " + videoAdUiPreSkipButtonFirstDiv.getText());

            videoAdUiPreSkipButtonSECONDDiv = driver

            time.sleep(random.randint(2,4))

            print("*************VISIBILITY OF THE ELEMENT 'YOU CAN SKIP ADD ' IS AFTER WAITING MORE THAN 5 SECONDS "
                + "************************* " + videoAdUiPreSkipButton.isDisplayed());

            skipaddbutton = driver.findElement(By.xpath("//div[@class='videoAdUiSkipContainer html5-stop-propagation']"));
            print("*************VISIBILITY OF THE ELEMENT FOR SKIP ADD BUTTON" + "************************* " + skipaddbutton.isDisplayed());
            print("*************VISIBILITY OF THE ELEMENT FOR SKP ADD BUTTON " + "************************* " + skipaddbutton.getText());

            skipaddbutton.click();

            time.sleep(random.randint(2,4));

        else: 
            print( "+++++++++++++video Doesn not have Skip Add button and It is Stopped in Second Catch Block +++++++++++++++++++++++++++");

    
    except:
        print("+++++++++++++video Doesn not have Skip Add button and it is not monextized and I am terminating Program in First excepion Block +++++++++++++++++++++++++++");
        pass
    

   
    
    
def main():
    global parser
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query', help='The start search query')
    parser.add_argument('--prequery', default='')
    parser.add_argument('--trending', default=False)
    parser.add_argument('--browsing', default='')
    parser.add_argument('--order', default='0', type=int, help='Order in which videos will be explore (-1,last; 0,normal, 1,random)')
    parser.add_argument('--name', help='Name given to the file')
    parser.add_argument('--searches', default='5', type=int, help='The number of search results to start the exploration')
    parser.add_argument('--branch', default='3', type=int, help='The branching factor of the exploration')
    parser.add_argument('--depth', default='5', type=int, help='The depth of the exploration')
    parser.add_argument('--alltime', default=False, type=bool, help='If we get search results ordered by highest number of views')
    parser.add_argument('--gl', help='Location passed to YouTube e.g. US, FR, GB, DE...')
    parser.add_argument('--language', help='Languaged passed to HTML header, en, fr, en-US, ...')
    parser.add_argument('--recent', default=False, type=bool, help='Keep only videos that have less than 1000 views')
    parser.add_argument('--security', default=3, type=int, help='2: normal; 3:privaty)
    parser.add_argument('--loopok', default=False, type=bool, help='Never loops back to the same videos.')
    parser.add_argument('--makehtml', default=False, type=bool,
        help='If true, writes a .html page with the name which compare most recommended videos and top rated ones.')

    args = parser.parse_args()

    if args.loopok:
        print('INFO We will print keys - ' + repr(args.loopok))
    else:
        print('INFO We will NOT be printing keys - ' + repr(args.loopok))

    chrome_options = Options()
    if args.security == 3:
        chrome_options.add_argument("--incognito")
    browser = webdriver.Chrome()

    if args.browsing == 't':
        print('Browsing trend videos top ' + str(args.searches))
        view_trending(browser,int(args.searches))
    elif len(args.browsing)>2:
        print('Browsing list of videos ' + str(args.browsing))
        browser_urls(browser, str(args.browsing))
        
    if len(args.prequery)>1:
        print('Browsing list of queries ' + str(args.prequery))
        view_searching(browser, str(args.prequery))
        
    try:
    	compare_keywords(browser, args.query, args.searches, args.branch, args.depth, args.name, args.gl, args.language, args.recent, args.loopok, args.trending,args.order)
    	browser.close()
    except:	
		browser.close()
		
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
