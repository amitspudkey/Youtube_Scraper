from file_handling import *
from selection import *
import pafy
import os
import youtube_dl
import pandas as pd
import re
import shutil
import ffmpeg

print("Program: BN_Youtube_Scraper")
print("Release: 0.0.9")
print("Date: 2020-03-30")
print("Author: Brian Neely")
print()
print()
print("This program reads a csv file of youtube url's and downloads them.")
print("Add ffmpeg.exe or install ffmpeg through command line before using this script/")
print()
print()

# Select CSV to open
file_in = select_file_in()

# Ask for delimination
delimiter = input("Please input Delimiter: ")

# Open CSV
data = open_unknown_csv(file_in, delimiter)

# Get header list
headers = list(data)

# URL column name
url_column_name = column_selection(headers, "YouTube URL scraping")

# Select URL column
url_list = data[url_column_name]

# Specify folder names
outpt_fldr = 'output'

# If output folder doesn't exist, create it.
if not os.path.exists(outpt_fldr):
    print()
    print("Output folder doesn't exist. Create output folder now...")
    os.mkdir(outpt_fldr)
    print()

# Initialize list of dictionaries for stats
stats_dict_list = list()

# Quality list
quality_dict = {'16k': '15360', '8k': '7680', '4k': '3840', '1440P': '2560', '1080P': '1920', '720P': '1280', '480P': '854',
                '360P': '640', '240P': '426'}

# Ask for quality
if y_n_question("Use best quality (y/n): "):
    video_quality_selection = list(quality_dict.keys())[0]
else:
    # Ask for best quality to be used
    video_quality_selection = dict_selection(quality_dict, "Select the maximum video quality to download", "")

# Ask for sound
if y_n_question("Include sound (This increasing processing time) (y/n): "):
    sound_selection = True
else:
    sound_selection = False

# Could not scrape limit
error_limit = 10
error_num = 0

# Could not scrape list
error_url_list = list()

# Loop through urls and scrap
for index, url in enumerate(url_list):
    # Try to scrape video
    print(url)
    try:
        # Create video object
        video = pafy.new(url)

        # Get stats
        title = video.title
        views = video.viewcount
        author = video.author
        length = video.length
        likes = video.likes
        dislikes = video.dislikes
        description = video.description

        # Clean title of non-allowed characters
        title = re.sub('[^\w\-_\. ]', '_', title)

        # Create dict of stats
        stats = dict()
        stats = {'title': title, 'views': views, 'author': author, 'length': length, 'likes': likes,
                 'dislikes': dislikes, 'description': description, 'url': url}

        # Create flag variables for quality finding
        max_quality = False
        quality_found = False

        # Loop through qualities
        for i in quality_dict:
            # If the quality selected is the same as the one in the dictionary, that selected and subsequent values
            # meet the required quality maximum.
            if i == video_quality_selection:
                max_quality = True

            # If quality meets the maximum
            if max_quality:
                # Loop through available video qualities
                for j in video.videostreams:
                    # Find if it matches the selected quality and is a mp4
                    if str(j).find(quality_dict[i]) != -1 and str(j).find('webm') != -1:
                        # Set quality output as the first found
                        quality_for_title = str(i)

                        # Set video out
                        video_out = j

                        # Set flag to break the next loop
                        quality_found = True
                        break

            # If the highest quality is found, break the dictionary loop
            if quality_found:
                break

        print(title + ": " + str(video_out))

        # Make title
        extension = '.' + video_out.extension
        full_title = title + " - " + quality_for_title + extension

        # If sound, Download best audio and combine with video
        if sound_selection:
            # Get best audio
            sound = video.getbestaudio()

            # Make temp folder
            temp_fldr = "temp"
            if os.path.exists(temp_fldr):
                print("Deleting old temp folder...")
                shutil.rmtree(temp_fldr)
                print("Old temp folder deleted!")
                print()
            time.sleep(2)
            print("Creating temporary folder...")
            os.mkdir(temp_fldr)

            # Temp File Locations
            video_path = os.path.join(temp_fldr, title + "video." + video_out.extension)
            audio_path = os.path.join(temp_fldr, title + "sound." + sound.extension)

            # Download audio and video into temp folder
            video_out.download(video_path)
            sound.download(audio_path)

            # Output Location
            output_path = os.path.join(outpt_fldr, full_title)

            # If file already present delete append a number at the end
            if os.path.exists(output_path):
                file_index = 1
                while os.path.exists(os.path.splitext(output_path)[0] + " - " + str(file_index) +
                                     os.path.splitext(output_path)[1]):
                    file_index = file_index + 1

                output_path = os.path.splitext(output_path)[0] + " - " + str(file_index) + \
                              os.path.splitext(output_path)[1]

            try:
                # Combine audio and video together
                input_video = ffmpeg.input(video_path)
                input_audio = ffmpeg.input(audio_path)
                ffmpeg.output(input_video, input_audio, output_path, vcodec='copy').run()
            except FileNotFoundError:
                print("Could not open ffmpeg. Please ffmpeg in the root directory and try again, run [brew install ffmpeg].")

            # Delete temp folder
            if os.path.exists(temp_fldr):
                try:
                    shutil.rmtree(temp_fldr)
                except:
                    print("Temporary folder could not be deleted.")
        else:
            # Download the video
            video_out.download(os.path.join(outpt_fldr, full_title))

        # Append stats to dict list
        stats_dict_list.append(stats)

        # Print Statement of progress
        print("Downloaded " + str(index + 1) + " of " + str(len(url_list)))
        print()
        print()
        print()

        # Reset error_num
        error_num = 0

        # Sleep 10 seconds to help limit HTTP Error 429
        time.sleep(10)

    except:
        print('Could not scrape: ' + url)
        if error_num < error_limit:
            print('Error ' + str(error_num) + ' in a row. After ' + str(error_limit) +
                  ' errors in a row, the script will stop.')
            print()
            error_num = error_num + 1
            error_url_list.append(url)
        else:
            print('Error limit reached. This is most likely due to a limit of the YouTube Data API Quota.')
            print('Once the quota is is restored, rerun the program on the "Unable_to_scrape_list.csv"')
            error_url_list = error_url_list + list(url_list[index:])
            break

# Convert stats_dict_list to dataframe
stats_df = pd.DataFrame(stats_dict_list)

# Write stats to a csv
stats_df.to_csv('stats.csv', index=False)

# Create Unable_to_scrape_list DF
unable_to_scrape = data[data[url_column_name].isin(error_url_list)]

# Write Unable_to_scrape_list to a csv
unable_to_scrape.to_csv('Unable_to_scrape_list.csv', index=False)
