# Discord Chat Exporter JSON to HTML

### This script is used to convert the export the json data converted by [Discord Chat Exporter by Tyrrrz](https://github.com/Tyrrrz/DiscordChatExporter) to HTML format.

## How To ?

1. Download this repository.
2. Put your JSON files and Media Folders in [InputFiles](./InputFiles/) folder.
   ![](https://i.imgur.com/6jtoybm.png)

## To convert a single json file to html

1. Open terminal in this folder. 
2. Run `pip install -r requirements.txt`
3. Run 
   > `python convert_single_file.py "Servername - CategoryName - ChannelName [ChannelID].json"`
4. Your converted HTML file will be in [InputFiles Directory](./InputFiles/).
   ![](https://i.imgur.com/3XCL7n6.png)
   
## To convert all json files present in [InputFiles Directory](./InputFiles/) to html

1. Click on [converall.bat](./convertall.bat) file and your files will be converted to HTML
   ![](https://i.imgur.com/73CjY8O.gif)
   
### Note: For better results, when you export the json files using Discord Chat Exporter, Use `--markdown false` flag.

## Pro Tips:
1. Export Command i use [DCE CLI]:
> `dotnet DiscordChatExporter.Cli.dll export -c channel_id -f Json -t "BotToken" --media --reuse-media --markdown false` 

---

Credits:
1. [Tyrrrz for DCE and CSS](https://github.com/Tyrrrz)
2. [Slatinsky for Example Guild (taken from his repo lol) and CSS](https://github.com/slatinsky)
