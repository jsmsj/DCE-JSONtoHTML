import os,json,datetime,mimetypes
import sys

from discord_markdown_ast_parser import parse_to_dict,parse
from discord_markdown_ast_parser.parser import Node,NodeType
import html
import re
import uuid,requests


anim_emoji_patt = re.compile(r'<a:(\w+):(\d{17,20})>')
url_pattern = re.compile(r'^https?://(?:discord|discordapp)\.com/channels/.*?/(\d+)/?$')
def replace_anim_emoji_with_uuid(msg):
    matches = anim_emoji_patt.findall(msg)
    new_str = msg
    location_of_anim_emoji = {} 
    if len(matches)!=0:
        for match in matches:
            x = str(uuid.uuid4())
            tmp = location_of_anim_emoji.get(f'<a:{match[0]}:{match[1]}>')
            if tmp:
                location_of_anim_emoji[f'<a:{match[0]}:{match[1]}>'].append(x)
            else:
                location_of_anim_emoji[f'<a:{match[0]}:{match[1]}>'] = [x]
                # location_of_anim_emoji[f'<a:{match[0]}:{match[1]}>'].append(x)
            
            new_str = new_str.replace(f'<a:{match[0]}:{match[1]}>',x,1)
    return new_str,location_of_anim_emoji

markdown_clicky_link_patt = re.compile(r'\[(.*)\]\((.*)\)')

def replace_clicky_with_uuid(msg):
    matches = markdown_clicky_link_patt.findall(msg)
    new_str = msg
    location_of_clicky_link = {} 
    if len(matches)!=0:
        for match in matches:
            x = str(uuid.uuid4())
            tmp = location_of_clicky_link.get(f'[{match[0]}]({match[1]})')
            if tmp:
                location_of_clicky_link[f'[{match[0]}]({match[1]})'].append(x)
            else:
                location_of_clicky_link[f'[{match[0]}]({match[1]})'] = [x]
            
            new_str = new_str.replace(f'[{match[0]}]({match[1]})',x,1)
    return new_str,location_of_clicky_link


def resolve_node(node:Node,len_ast):
    if node.node_type == NodeType.TEXT:
        temp = html.escape(node.text_content) 
        return temp if temp !=None else ''
    elif node.node_type == NodeType.BOLD:
        temp = "".join([resolve_node(child,len_ast) for child in node.children])
        return f'<strong>{temp}</strong>'
    elif node.node_type == NodeType.UNDERLINE:
        temp = "".join([resolve_node(child,len_ast) for child in node.children])
        return f'<u>{temp}</u>'
    elif node.node_type == NodeType.ITALIC:
        temp = "".join([resolve_node(child,len_ast) for child in node.children])
        return f'<em>{temp}</em>'
    elif node.node_type == NodeType.STRIKETHROUGH:
        temp = "".join([resolve_node(child,len_ast) for child in node.children])
        return f'<s>{temp}</s>'
    elif node.node_type == NodeType.SPOILER:
        temp = "".join([resolve_node(child,len_ast) for child in node.children])
        return f'<span class="chatlog__markdown-spoiler chatlog__markdown-spoiler--hidden" onclick="showSpoiler(event, this)">{temp}</span>'
    elif node.node_type == NodeType.QUOTE_BLOCK:
        temp = "".join([resolve_node(child,len_ast) for child in node.children])
        return f'<div class="chatlog__markdown-quote"><div class="chatlog__markdown-quote-border"></div><div class="chatlog__markdown-quote-content">\n{temp}\n</div></div>'
    elif node.node_type == NodeType.CODE_INLINE:
        temp = "".join([resolve_node(child,len_ast) for child in node.children])
        return f'<code class="chatlog__markdown-pre chatlog__markdown-pre--inline">{temp}</code>'
    elif node.node_type == NodeType.CODE_BLOCK:
        temp = "".join([resolve_node(child,len_ast) for child in node.children])
        highlight_class = f"language-{node.code_lang}" if node.code_lang else "nohighlight"
        return f'<code class="chatlog__markdown-pre chatlog__markdown-pre--multiline {highlight_class}">{temp}</code>'
    elif node.node_type in [NodeType.URL_WITHOUT_PREVIEW,NodeType.URL_WITH_PREVIEW]:
        url = node.url
        matched = url_pattern.match(url)
        if matched:
            msg_id = matched.group(1)
        else:
            msg_id = None
        if msg_id:
            temp = f'<a href="{url}" onclick="scrollToMessage(event, \'{msg_id}\')">{url}'
        else:
            temp = f'<a href="{url}">{url}'
        
        temp+='</a>'
        return temp
    elif node.node_type  == NodeType.EMOJI_UNICODE_ENCODED:
        return f":{str(node.emoji_name)}:"
    elif node.node_type == NodeType.EMOJI_CUSTOM:
        if len_ast == 1:
            jumbo = True
        else:
            jumbo = False
        
        return f"""<img loading="lazy" class="chatlog__emoji {'chatlog__emoji--large' if jumbo else ''}" alt="{node.emoji_name}" title=":{node.emoji_name}:" src="https://cdn.discordapp.com/emojis/{node.discord_id}.png">"""
    elif node.node_type == NodeType.USER: #TODO
        discord_id = node.discord_id
        fullname = str(discord_id)
        nickname = str(discord_id)
        return f'<span class="chatlog__markdown-mention" title="{html.escape(fullname)}">@{html.escape(nickname)}</span>'
    elif node.node_type == NodeType.CHANNEL: #TODO
        discord_id = node.discord_id
        symbols = ["🔊" , "#"]
        name = str(discord_id)
        return f'<span class="chatlog__markdown-mention">{symbols[1]}{name}</span>'
    elif node.node_type == NodeType.ROLE: #TODO
        discord_id = node.discord_id
        name = str(discord_id)
        color = [255,0,255]
        style = f'color:rgb({color[0]},{color[1]},{color[2]}); background-color: rgba({color[0]},{color[1]},{color[2]},0.1)'
        return f'<span class="chatlog__markdown-mention" style="{style}">@{html.escape(name)}</span>'
    
# anim_emoji_patt = re.compile(r'(<a):\w+:(\d{17,20}>)')

# animated_emoji_pattern = re.compile(r'\&lt;a:(\w+):(\d{17,20})\&gt;')
# (<a):\w+:(\d{18}>)
# \&lt;a:(\w+):(\d{18})\&gt;

def anim_emoji_name_to_url(name,jumbo):
    matches = anim_emoji_patt.findall(name)
    if len(matches) == 0:
        return ''
    match = matches[0]
    return f"""<img loading="lazy" class="chatlog__emoji {'chatlog__emoji--large' if jumbo else ''}" alt="{match[0]}" title=":{match[0]}:" src="https://cdn.discordapp.com/emojis/{match[1]}.gif">"""

def fix_animated_emoji(message,anim_location,len_ast):

    if anim_location == {}:
        return message
    

    if len_ast == 1:
        jumbo = True
    else:
        jumbo = False

    for k,v in anim_location.items():
        for i in v:
            message = message.replace(i,anim_emoji_name_to_url(k,jumbo))
    
    return message


def clicky_link_to_html(txt):
    matches = markdown_clicky_link_patt.findall(txt)
    if len(matches) == 0:
        return ''
    match = matches[0]
    return f"""<a href="{match[1]}">{match[0]}</a>"""


def fix_clicky_links(message,clicky_location):
    if clicky_location == {}:
        return message

    for k,v in clicky_location.items():
        for i in v:
            message = message.replace(i,clicky_link_to_html(k))
    
    return message

def fix_everyone_and_here(message):
    return message.replace('@everyone','<span class="chatlog__markdown-mention">@everyone</span>').replace('@here','<span class="chatlog__markdown-mention">@everyone</span>')

def message_markdown(message_content,replace_newlines=False):
    
    message_semi_content,anim_location = replace_anim_emoji_with_uuid(message_content)
    message_final_content,clicky_location = replace_clicky_with_uuid(message_semi_content)

    message_final_content = message_final_content.replace('___','__').replace('***','**')
    try:
        ast = parse(message_final_content)
    except Exception as e:
        anim_fixed = fix_animated_emoji(message_final_content,anim_location,0)
        clicky_fixed = fix_clicky_links(anim_fixed,clicky_location)
        final = fix_everyone_and_here(clicky_fixed)
        if replace_newlines:
            final = final.replace('\n',' ')
        return final



    text = ''

    for node in ast:

        x = resolve_node(node,len(ast))

        text+= x

    anim_fixed = fix_animated_emoji(text,anim_location,len(ast))
    clicky_fixed = fix_clicky_links(anim_fixed,clicky_location)
    final = fix_everyone_and_here(clicky_fixed)
    if replace_newlines:
        final = final.replace('\n',' ')
    return final


    #TODO timestamp fix https://github.com/discordjs/discord-api-types/blob/main/globals.ts#L78-L90



name_of_file_to_load = sys.argv[1]

assets_folder = name_of_file_to_load+'_Files'

with open(f'InputFiles/{name_of_file_to_load}') as f:
    json_data = json.load(f)


messages = json_data['messages']
reply_like = ['reply','20']


system_message_types = ['recipientadd', 'recipientremove', 'call', 'channelnamechange', 'channeliconchange', 'channelpinnedmessage', 'userjoin', 'threadcreated']
system_message_classes = ["join-icon","leave-icon","call-icon","pencil-icon","pencil-icon","pin-icon","join-icon","thread-icon"]

def timestamp_to_dt_obj(timestamp):
    try:
        date_format = "%Y-%m-%dT%H:%M:%S.%f%z"
        return datetime.datetime.strptime(timestamp, date_format)
    except ValueError:
        date_format = "%Y-%m-%dT%H:%M:%S%z"
        return datetime.datetime.strptime(timestamp, date_format)

def handle_system_notification_content(message):

    if message['type'].lower() == 'recipientadd' and len(message['mentions'])!=0:
        return f"""
                <span>added </span>
                <a class="chatlog__system-notification-link" title="{message['mentions'][0]['name']}">{message['mentions'][0]['nickname']}</a>
                <span> to the group.</span>
"""
    elif message['type'].lower() == 'recipientremove' and len(message['mentions'])!=0:
        if message['mentions'][0]['id'] == message['author']['id']:
            return f"""
                <span>left the group.</span>            
"""
        else:
            return f"""
                <span>removed </span>
                <a class="chatlog__system-notification-link" title="{message['mentions'][0]['name']}">{message['mentions'][0]['nickname']}</a>
                <span> from the group.</span>
"""
    
    elif message['type'].lower() == 'call':
        return f"""
                <span>started a call that lasted {((timestamp_to_dt_obj(message['callEndedTimestamp']) if message['callEndedTimestamp'] is not None else timestamp_to_dt_obj(message['timestamp'])) - timestamp_to_dt_obj(message['timestamp'])).total_seconds() / 60} minutes</span>
"""
    elif message['type'].lower() == 'channelnamechange':
        return f"""
                <span>changed the channel name: </span>
                <span class="chatlog__system-notification-link">{message['content']}</span>
"""
    elif message['type'].lower() == 'channeliconchange':
        return f"""
                <span>changed the channel icon.</span>        
"""
    elif message['type'].lower() == 'channelpinnedmessage' and message.get("reference") is not None:
        return f"""
                <span>pinned </span>
                <a class="chatlog__system-notification-link" href="#chatlog__message-container-{message['reference']['messageId']}">a message</a>
                <span> to this channel.</span>
"""
    elif message['type'].lower() == 'userjoin':
        return f"""
                <span>joined the server.</span>
"""
    elif message['type'].lower() == 'threadcreated':
        return f"""
                <span>started a thread.</span>        
"""

def get_formatted_date(timestamp):
    dt_obj = timestamp_to_dt_obj(timestamp)
    return datetime.datetime.strftime(dt_obj,'%d-%b-%y %I:%M %p')

def get_short_timestamp(timestamp):
    dt_obj = timestamp_to_dt_obj(timestamp)
    return datetime.datetime.strftime(dt_obj,'%H:%M')



def handle_system_message(message):
    txt = f"""
        <div class="chatlog__message-aside">
            <svg class="chatlog__system-notification-icon">
                <use href="{system_message_classes[system_message_types.index(message['type'].lower())]}"></use>
            </svg>
        </div>
        <div class="chatlog__message-primary">
            <span class="chatlog__system-notification-author" style="{'' if message['author']['color'] is None else 'color:' + message['author']['color']}" title="{message['author']['name']}" data-user-id="{message['author']['id']}">{message['author']['nickname']}</span>

            <span> </span>

            <span class="chatlog__system-notification-content">

                {handle_system_notification_content(message)}

            </span>

            <span class="chatlog__system-notification-timestamp">
                        <a href="#chatlog__message-container-{message['id']}">{get_formatted_date(message['timestamp'])}</a>
            </span>
        </div>
"""
    return txt


def find_message(message_id):
    for msg in messages:
        if msg['id'] == message_id:
            return msg
    return None

def handle_reply_primary_1(message): 
    if message.get('reference') is not None:
        referred_msg_id = message['reference']['messageId']
        referred_message = find_message(referred_msg_id)

        if referred_message:
            try:
                tmp1 = f"color:{referred_message['author']['color']};"
            except KeyError:
                tmp1 = ''
            txt = f"""
                <img class="chatlog__reference-avatar" src="{referred_message['author']['avatarUrl']}" alt="Avatar" loading="lazy" onerror="this.style.visibility='hidden'" width="16" height="16">
                <div class="chatlog__reference-author" style="{tmp1}" title="{referred_message['author']['name']}">{referred_message['author']['nickname']}</div>
                <div class="chatlog__reference-content">
                    <span class="chatlog__reference-link" onclick="scrollToMessage(event, '{message['reference']['messageId']}')">
                        {'Click to see original message/attachment' if not referred_message else message_markdown(referred_message['content'],replace_newlines=True)}
                    </span>
                    {f'<span class="chatlog__reply-edited-timestamp" title="{get_formatted_date(referred_message["timestampEdited"])}">(edited)</span>' if referred_message['timestampEdited'] is not None else ''}
                </div>
"""     
        else:
            txt = f"""
                <div class="chatlog__reference-unknown">
                    Original message was deleted or could not be loaded.
                </div>
"""
    elif message.get('interaction') is not None:
        try:
            tmp1 = f"color:{message['interaction']['user']['color']};"
        except KeyError:
            tmp1 = ''
        txt = f"""
                <img class="chatlog__reference-avatar" src="{message['interaction']['user']['avatarUrl']}" alt="Avatar" loading="lazy">
                <div class="chatlog__reference-author" style="{tmp1}" title="{message['interaction']['user']['name']}">{message['interaction']['user']['nickname']}</div>
                <div class="chatlog__reference-content">
                    used /{message['interaction']['name']}
                </div>
"""

    else:
        txt = f"""
                <div class="chatlog__reply-unknown">
                    Original message was deleted or could not be loaded.
                </div>
"""
    return txt


def handle_content(message):
    txt = f"""
                <div class="chatlog__content chatlog__markdown">
                    {f'<span class="chatlog__markdown-preserve">{message_markdown(message["content"])}</span>' if not message['content'] == '' else ''}
                    {f'<span class="chatlog__edited-timestamp" title="{get_formatted_date(message["timestampEdited"])}">(edited)</span>' if message['timestampEdited'] is not None else ''}
                </div>
"""
    return txt


def handle_single_attachment(attachment):
    mimeType = mimetypes.guess_type(attachment['fileName'])[0]
    

    if attachment['fileName'].startswith('SPOILER'):
        txt1 = f"""
                    <div class="chatlog__attachment-spoiler-caption">SPOILER</div>
"""
    else:
        txt1 = ''

    if mimeType is not None:
        if 'image' in mimeType:
            txt = f"""
                    <a href="{attachment['url']}">
                        <img class="chatlog__attachment-media" src="{attachment['url']}" alt="Image attachment" title="Image: {attachment['fileName']} ({attachment['fileSizeBytes']} Bytes)" loading="lazy">
                    </a>
"""
        elif 'video' in mimeType:
            txt = f"""
                    <video class="chatlog__attachment-media" controls>
                        <source src="{attachment['url']}" alt="Video attachment" title="Video: {attachment['fileName']} ({attachment['fileSizeBytes']} Bytes)">
                    </video>
"""
        elif 'audio' in mimeType:
            txt = f"""
                    <audio class="chatlog__attachment-media" controls>
                        <source src="{attachment['url']}" alt="Audio attachment" title="Audio: {attachment['fileName']} ({attachment['fileSizeBytes']} Bytes)">
                    </audio>
"""
        else:
            txt = f"""
                    <div class="chatlog__attachment-generic">
                        <svg class="chatlog__attachment-generic-icon">
                            <use href="#attachment-icon"/>
                        </svg>
                        <div class="chatlog__attachment-generic-name">
                            <a href="{attachment['url']}">
                                {attachment['fileName']}
                            </a>
                        </div>
                        <div class="chatlog__attachment-generic-size">
                            {attachment['fileSizeBytes']} Bytes
                        </div>
                    </div>
"""
    else:
        txt = f"""
                    <div class="chatlog__attachment-generic">
                        <svg class="chatlog__attachment-generic-icon">
                            <use href="#attachment-icon"/>
                        </svg>
                        <div class="chatlog__attachment-generic-name">
                            <a href="{attachment['url']}">
                                {attachment['fileName']}
                            </a>
                        </div>
                        <div class="chatlog__attachment-generic-size">
                            {attachment['fileSizeBytes']} Bytes
                        </div>
                    </div>
"""
    return txt1+txt


def handler_for_attachments(message):
    return "\n\n".join([f"""
                <div class="chatlog__attachment {'chatlog__attachment--hidden' if attachment['fileName'].startswith('SPOILER') else ''}" {'onclick="showSpoiler(event, this)"' if attachment['fileName'].startswith('SPOILER') else ''}>
                    {handle_single_attachment(attachment)}
                </div>
""" for attachment in message["attachments"]])


def handle_reply_primary(message):
    txt = f"""
            <div class="chatlog__reference">

                {handle_reply_primary_1(message)}
              
            </div>
"""
    return txt

def handle_first_primary(message):
    txt = f"""
            {handle_reply_primary(message) if message['type'].lower() in reply_like else ''}

            <div class="chatlog__header">

                <span class="chatlog__author" style="{'' if message['author']['color'] is None else 'color:' + message['author']['color']}" title="{message['author']['name']}" data-user-id="{message['author']['id']}">{message['author']['nickname']}</span>
                {'<span class="chatlog__author-tag">BOT</span>' if message['author']['isBot'] else ''}
                <span class="chatlog__timestamp"><a href="#chatlog__message-container-{message['id']}">{get_formatted_date(message['timestamp'])}</a></span>
            </div>
"""
    return txt

def handle_emb_author_link(embed):
    if not embed['author'].get('url') in [None,'']:
        txt = f"""
                                <a class="chatlog__embed-author-link" href="{embed['author']['url']}">
                                    <div class="chatlog__embed-author">{embed['author']['name']}</div>
                                </a>
"""
    else:
        txt = f"""
                                <div class="chatlog__embed-author">{embed['author']['name']}</div>
"""
    return txt


def handle_emb_author(embed): 
    messingup_txt_1 = """onerror="this.style.visibility='hidden'" width="16" height="16">"""
    author_icon_url = f"{embed['author'].get('iconUrl') if embed['author'].get('iconUrl') not in ['',None] else ''}"
    txt = f"""
                            <div class="chatlog__embed-author-container">
                                {f'<img class="chatlog__embed-author-icon" src="{author_icon_url}" alt="Author icon" loading="lazy"' + messingup_txt_1 if embed['author']['url'] is not None else ''}
                                {handle_emb_author_link(embed) if embed['author'].get('name') not in [None,''] else ''}
                            </div>
"""
    return txt

def handle_emb_title_link(embed):
    txt = f"""
                                <a class="chatlog__embed-title-link" href="{embed['url']}">
                                    <div class="chatlog__markdown chatlog__markdown-preserve">{embed['title']}</div>
                                </a>
"""
    return txt

def handle_emb_title(embed):
    txt = f"""
                            <div class="chatlog__embed-title">
                                {handle_emb_title_link(embed) if embed.get('url') not in [None,''] else f'<div class="chatlog__markdown chatlog__markdown-preserve">{embed["title"]}</div>'}
                            </div>
"""
    return txt


def handle_emb_description(embed):
    txt = f"""
                            <div class="chatlog__embed-description">
                                <div class="chatlog__markdown chatlog__markdown-preserve">{message_markdown(embed['description'])}</div>
                            </div>
"""
    return txt

def handle_emb_field(field):
    txt = f"""
                                <div class="chatlog__embed-field {"chatlog__embed-field--inline" if field['isInline'] else ''}">
                                    <div class="chatlog__embed-field-name">
                                        <div class="chatlog__markdown chatlog__markdown-preserve">{field['name']}</div>
                                    </div>
                                    <div class="chatlog__embed-field-value">
                                        <div class="chatlog__markdown chatlog__markdown-preserve">{message_markdown(field['value'])}</div>
                                    </div>
                                </div>

"""
    return txt


def handler_for_embed_fields(embed):
    return '\n\n'.join(
        [handle_emb_field(field) for field in embed['fields']]
    )

def handle_embed_thumbnail(embed):
    txt = f"""
                        <div class="chatlog__embed-thumbnail-container">
                            <a class="chatlog__embed-thumbnail-link" href="{embed['thumbnail']['url']}">
                                <img class="chatlog__embed-thumbnail" src="{embed['thumbnail']['url']}" alt="Thumbnail" loading="lazy">
                            </a>
                        </div>
"""
    return txt


def handle_embed_image(image):
    txt = f"""
                        <div class="chatlog__embed-image-container">
                            <a class="chatlog__embed-image-link" href="{image['url']}">
                                <img class="chatlog__embed-image" src="{image['url']}" alt="Image" loading="lazy">
                            </a>
                        </div>
"""
    return txt


def handler_for_images(embed):
    return '\n\n'.join(
        [handle_embed_image(img) for img in embed['images'] if img.get('url') not in [None,''] ]
    )

def handle_emb_timestamp_and_footer(embed):
    if embed.get('footer') in ['',None]:
        return ''
    if embed.get('timestamp') in ['',None]:
        return ''
    if embed['footer'].get('iconUrl') not in [None,'']:
        footer_icon_url = f"{embed['footer'].get('iconUrl')}"
    else:
        footer_icon_url = ''
    txt = f"""
                    <div class="chatlog__embed-footer">
                        {f'<img class="chatlog__embed-footer-icon" src="{footer_icon_url}" alt="Footer icon" loading="lazy">' if embed['footer'].get('iconUrl') not in [None,''] else ''}

                        <span class="chatlog__embed-footer-text">

                            {embed['footer'].get('text') if embed['footer'].get('text') not in [None,''] else ''}
                            {" • " if embed['footer'].get('text') not in [None,''] and embed['timestamp'] not in [None,''] else ''}
                            {datetime.datetime.strftime(timestamp_to_dt_obj(embed['timestamp']),'%d/%m/%Y %I:%M %p') if embed['timestamp'] not in [None,''] else ''}
                        </span>

                    </div>
"""
    return txt


def handle_embeds(embed):
    emb_url = embed['url']

    if not emb_url:
        _type = 'rich'
    elif 'open.spotify.com' in emb_url:
        _type = 'spotify'
    elif 'youtube.com' in emb_url and not ('youtube.com/channel' in emb_url or 'youtube.com/@' in emb_url):
        _type = 'youtube'
    else:
        _type = 'rich'

    if _type == 'spotify':
        txt = f"""
            <div class="chatlog__embed">
                <div class="chatlog__embed-spotify-container">
                    <iframe class="chatlog__embed-spotify" src="{embed['url']}" width="400" height="80" allowtransparency="true" allow="encrypted-media"></iframe>
                </div>
            </div> 
"""
    elif _type == 'youtube':
        txt = f"""
            <div class="chatlog__embed">
                <div class="chatlog__embed-color-pill chatlog__embed-color-pill--default"></div>
                <div class="chatlog__embed-content-container">
                    <div class="chatlog__embed-content">
                        <div class="chatlog__embed-text">
                            {handle_emb_author(embed) if embed.get('author') not in [None,''] else ''}
                            {handle_emb_title(embed) if embed.get('title') not in [None,''] else ''}
                            <div class="chatlog__embed-youtube-container">
                                <iframe class="chatlog__embed-youtube" src="{embed['url'].replace('https://www.youtube.com/watch?v=','https://www.youtube.com/embed/')}" width="400" height="225"></iframe>
                            </div>
                        </div>
                    </div>
                </div>
            </div> 
"""
    else: # rich embed
        txt = f"""
            <div class="chatlog__embed">
                {f'<div class="chatlog__embed-color-pill" style="background-color: {embed["color"]}"></div>' if embed.get('color') not in [None,''] else '<div class="chatlog__embed-color-pill chatlog__embed-color-pill--default"></div>'}
                <div class="chatlog__embed-content-container">
                    <div class="chatlog__embed-content">
                        <div class="chatlog__embed-text">
                            {handle_emb_author(embed) if embed.get('author') not in [None,''] else ''}
                            {handle_emb_title(embed) if embed.get('title') not in [None,''] else ''}
                            {handle_emb_description(embed)if embed.get('description') not in [None,''] else ''}
                            <div class="chatlog__embed-fields">
                                {handler_for_embed_fields(embed) if len(embed['fields']) !=0 else ''}
                            </div>
                        </div>
                        {handle_embed_thumbnail(embed) if embed.get('thumbnail') not in [None,''] and embed.get('thumbnail').get('url') not in [None,''] else ''}
                    </div>
                    <div class="chatlog__embed-images {"chatlog__embed-images--single" if len(embed['images']) == 1 else ''}">
                        {handler_for_images(embed) if len(embed['images']) !=0 else ''}
                    </div>

                    {handle_emb_timestamp_and_footer(embed) if embed.get('footer') not in [None,''] or embed.get('timestamp') not in [None,''] else ''}

                </div>
            </div>
"""


    return txt

def handler_for_embeds(message):
    if len(message['embeds']) == 0:return ''
    return '\n\n'.join([
        handle_embeds(embed) for embed in message['embeds']
    ])


def handle_sticker(sticker):
    txt = f"""
            <div class="chatlog__sticker" title="{sticker['name']}">
                <img class="chatlog__sticker--media" src="{sticker['sourceUrl']}" alt="Sticker">
            </div>

"""
    return txt


def handler_for_stickers(message):
    return '\n\n'.join([
        handle_sticker(sticker) for sticker in message['stickers']
    ])


def handle_reaction(reaction): 
    txt = f"""
                <div class="chatlog__reaction" title="{reaction['emoji']['name']}">
                    <img class="chatlog__emoji chatlog__emoji--small" alt="{reaction['emoji']['name']}" src="{reaction['emoji']['imageUrl']}" loading="lazy">
                    <span class="chatlog__reaction-count">{reaction['count']}</span>
                </div>
"""
    return txt


def handler_for_reactions(message):
    return '\n\n'.join([
        handle_reaction(reaction) for reaction in message['reactions']
    ])


def handle_first_aside(message): 
    txt = f"""
            {'<div class="chatlog__reference-symbol"></div>' if message['type'].lower() in reply_like else ''}
            <img class="chatlog__avatar" src="{message['author']['avatarUrl']}" alt="Avatar" loading="lazy">
"""
    return txt

def handle_message(message,m_index):  #NOTE/TODO Invites not yet supported #if m_index == 0 else
    txt = f"""
        <div class="chatlog__message-aside">
            {handle_first_aside(message) + f'<div class="chatlog__short-timestamp" title="{get_short_timestamp(message["timestamp"])}">{get_short_timestamp(message["timestamp"])}</div>'}
        </div>

        <div class="chatlog__message-primary">
            {handle_first_primary(message)}

            {handle_content(message) if not message['content'] == '' or message['timestampEdited'] is not None else ''}

            {handler_for_attachments(message)}

            {handler_for_embeds(message)}

            {handler_for_stickers(message)}
            <div class="chatlog__reactions">
                {handler_for_reactions(message)}
            </div>
        </div>
"""
    return txt


total_messages = len(messages)

def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()


printProgressBar(0, total_messages, prefix = 'Progress:', suffix = 'Complete', length = 50)

guild_name = json_data['guild']['name']
guild_iconurl = json_data['guild']['iconUrl']
channel_category = json_data['channel']['category']
channel_name = json_data['channel']['name']


try:
    style_css = requests.get('https://raw.githubusercontent.com/jsmsj/DCE-JSONtoHTML/master/style.css').text
except:
    style_css = """
    
:root {
	--font: Whitney, "Helvetica Neue", Helvetica, Arial, sans-serif;
}

:root[data-font="ggsans"] {
	--font: "gg sans", Whitney, "Helvetica Neue", Helvetica, Arial, sans-serif;
}

:root[data-font="arial"] {
	--font: Arial, "Helvetica Neue", Helvetica, sans-serif;
}

:root[data-font="timesnewroman"] {
	--font: "Times New Roman", "Helvetica Neue", Helvetica, Arial, sans-serif;
}

:root[data-font="comicsans"] {
	--font: "Comic Sans MS", "Comic Sans", "Helvetica Neue", Helvetica, Arial, sans-serif;
}

:root[data-theme="dark"] {
	--color-discord-blue: #5865F2;
	--color-discord-green: #3BA55D;

	--color-text: #DCDDDE;
	--color-contrast: white;
	--color-bg: #36393F;

	--channel-text-read: #8E9297;
	--channel-text-read-hover: #DCDDDE;
	--channel-text-unread: white;
	--channel-bg-hover: #3C3F45;

	--header-icon: #B9BBBE;
	--header-icon-hover: #DCDDDE;

	--panel-guilds-bg: #202225;
	--panel-channels-bg: #2F3136;
	--panel-messages-bg: #36393F;

	--ping-bg: #414675;
	--ping-bg-hover: #5865F2;
	--ping-text: #DEE0FC;
	--ping-text-hover: white;

	--msg-link: #00AFF4;

	--message-hover-bg: #32353b;

	--borders: rgba(255, 255, 255, 0.1);
	--borders2: #4f545c;
}

:root[data-theme="black"] {
	--color-discord-blue: #5865F2;
	--color-discord-green: #3BA55D;

	--color-text: #DCDDDE;
	--color-contrast: white;
	--color-bg: black;

	--channel-text-read: #8E9297;
	--channel-text-read-hover: #DCDDDE;
	--channel-text-unread: white;
	--channel-bg-hover: #3C3F45;

	--header-icon: #B9BBBE;
	--header-icon-hover: #DCDDDE;

	--panel-guilds-bg: rgb(8, 8, 8);
	--panel-channels-bg: rgb(8, 8, 8);
	--panel-messages-bg: black;

	--ping-bg: #414675;
	--ping-bg-hover: #5865F2;
	--ping-text: #DEE0FC;
	--ping-text-hover: white;

	--msg-link: #00AFF4;

	--message-hover-bg: #131313;

	--borders: rgba(255, 255, 255, 0.1);
	--borders2: #4f545c;
}

:root[data-theme="white"] {
	--color-discord-blue: #5865F2;
	--color-discord-green: #3BA55D;

	--color-text: #2e3338;
	--color-contrast: black;
	--color-bg: white;

	--channel-text-read: #5E6772;
	--channel-text-read-hover: #2E3338;
	--channel-text-unread: black;
	--channel-bg-hover: #DCDFE3;

	--header-icon: #B9BBBE;
	--header-icon-hover: #DCDDDE;

	--panel-guilds-bg: #E3E5E8;
	--panel-channels-bg: #F2F3F5;
	--panel-messages-bg: white;

	--message-hover-bg: #dddddd;


	--ping-bg: #414675;
	--ping-bg-hover: #5865F2;
	--ping-text: #DEE0FC;
	--ping-text-hover: white;

	--msg-link: #0068e0;

	--borders: #eceeef;
	--borders2: #c7ccd1;
}

@font-face {
	src: url(whitney-300);
	font-family: Whitney;
	font-weight: 300
}

@font-face {
	src: url(whitney-400);
	font-family: Whitney;
	font-weight: 400
}

@font-face {
	src: url(whitney-500);
	font-family: Whitney;
	font-weight: 500
}

@font-face {
	src: url(whitney-600);
	font-family: Whitney;
	font-weight: 600
}

@font-face {
	src: url(whitney-700);
	font-family: Whitney;
	font-weight: 700
}

@font-face {
	font-family: "gg sans";
	font-style: normal;
	font-weight: 400;
	src: url(ggsans-normal-400) format("woff2")
}

@font-face {
	font-family: "gg sans";
	font-style: italic;
	font-weight: 400;
	src: url(ggsans-italic-400) format("woff2")
}

@font-face {
	font-family: "gg sans";
	font-style: normal;
	font-weight: 500;
	src: url(ggsans-normal-500) format("woff2")
}

@font-face {
	font-family: "gg sans";
	font-style: italic;
	font-weight: 500;
	src: url(ggsans-italic-500) format("woff2")
}

@font-face {
	font-family: "gg sans";
	font-style: normal;
	font-weight: 600;
	src: url(ggsans-normal-600) format("woff2")
}

@font-face {
	font-family: "gg sans";
	font-style: italic;
	font-weight: 600;
	src: url(ggsans-italic-600) format("woff2")
}

@font-face {
	font-family: "gg sans";
	font-style: normal;
	font-weight: 700;
	src: url(ggsans-normal-700) format("woff2")
}

@font-face {
	font-family: "gg sans";
	font-style: italic;
	font-weight: 700;
	src: url(ggsans-italic-700) format("woff2")
}

@font-face {
	font-family: "gg sans";
	font-style: normal;
	font-weight: 800;
	src: url(ggsans-normal-800) format("woff2")
}

@font-face {
	font-family: "gg sans";
	font-style: italic;
	font-weight: 800;
	src: url(ggsans-italic-800) format("woff2")
}



html,
body {
	margin: 0;
	padding: 0;
	background-color: var(--color-bg);
	color: var(--color-text);
	font-family: var(--font);
	font-size: 17px;
	font-weight: 400;
	scroll-behavior: smooth
}

a {
	color: var(--msg-link);
	text-decoration: none
}

a:hover {
	text-decoration: underline
}

img {
	object-fit: contain;
	image-rendering: high-quality;
	image-rendering: -webkit-optimize-contrast
}

.chatlog {
	padding: 1rem 0;
	width: 100%;
	border-top: 1px solid var(--borders);
	border-bottom: 1px solid var(--borders)
}

.chatlog__message-group {
	margin-bottom: 1rem
}

.chatlog__message-container {
	background-color: transparent;
	transition: background-color 1s ease
}

.chatlog__message-container--highlighted {
	background-color: rgba(114, 137, 218, 0.2)
}

.chatlog__message-container--pinned {
	background-color: rgba(249, 168, 37, 0.05)
}

.chatlog__author-tag {
	position: relative;
	top: -0.1rem;
	margin-left: 0.3rem;
	padding: 0.05rem 0.3rem;
	border-radius: 3px;
	background-color: #5865F2;
	color: #ffffff;
	font-size: 0.625rem;
	font-weight: 500;
	line-height: 1.3;
}
.chatlog__message {
	display: grid;
	grid-template-columns: auto 1fr;
	padding: 0.15rem 0;
	direction: ltr;
	unicode-bidi: bidi-override
}

.chatlog__message:hover {
	background-color: var(--message-hover-bg)
}

/* .chatlog__message:hover .chatlog__short-timestamp {
	display: block
} */

.chatlog__message-aside {
	grid-column: 1;
	width: 72px;
	padding: 0.15rem 0.15rem 0 0.15rem;
	text-align: center
}

.chatlog__reference-symbol {
	height: 10px;
	margin: 6px 4px 4px 36px;
	border-left: 2px solid var(--borders2);
	border-top: 2px solid var(--borders2);
	border-radius: 8px 0 0 0
}

.chatlog__avatar {
	width: 40px;
	height: 40px;
	border-radius: 50%
}

.chatlog__short-timestamp {
	display: none;
	color: #a3a6aa;
	font-size: 0.75rem;
	font-weight: 500;
	direction: ltr;
	unicode-bidi: bidi-override
}

.chatlog__message-primary {
	grid-column: 2;
	min-width: 0
}

.chatlog__reference {
	display: flex;
	margin-bottom: 0.15rem;
	align-items: center;
	color: #b5b6b8;
	font-size: 0.875rem;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis
}

.chatlog__reference-avatar {
	width: 16px;
	height: 16px;
	margin-right: 0.25rem;
	border-radius: 50%
}

.chatlog__reference-author {
	margin-right: 0.3rem;
	font-weight: 600
}

.chatlog__reference-content {
	overflow: hidden;
	text-overflow: ellipsis
}

.chatlog__reference-link {
	cursor: pointer
}

.chatlog__reference-link * {
	display: inline;
	pointer-events: none
}

.chatlog__reference-link .chatlog__markdown-quote {
	display: inline
}

.chatlog__reference-link .chatlog__markdown-pre {
	display: inline
}

.chatlog__reference-link:hover {
	color: #ffffff
}

.chatlog__reference-link:hover *:not(.chatlog__markdown-spoiler) {
	color: inherit
}

.chatlog__reference-edited-timestamp {
	margin-left: 0.25rem;
	color: #a3a6aa;
	font-size: 0.75rem;
	font-weight: 500;
	direction: ltr;
	unicode-bidi: bidi-override
}

.chatlog__system-notification-icon {
	width: 18px;
	height: 18px
}

.chatlog__system-notification-author {
	font-weight: 500;
	color: #ffffff
}

.chatlog__system-notification-content {
	color: #96989d
}

.chatlog__system-notification-link {
	font-weight: 500;
	color: #ffffff
}

.chatlog__system-notification-timestamp {
	margin-left: 0.3rem;
	color: #a3a6aa;
	font-size: 0.75rem;
	font-weight: 500;
	direction: ltr;
	unicode-bidi: bidi-override
}

.chatlog__system-notification-timestamp a {
	color: inherit
}

.chatlog__header {
	margin-bottom: 0.1rem
}

.chatlog__author {
	font-weight: 500;
	color: var(--color-contrast)
}

.chatlog__bot-label {
	position: relative;
	top: -0.1rem;
	margin-left: 0.3rem;
	padding: 0.05rem 0.3rem;
	border-radius: 3px;
	background-color: #5865F2;
	color: #ffffff;
	font-size: 0.625rem;
	font-weight: 500;
	line-height: 1.3
}

.chatlog__timestamp {
	margin-left: 0.3rem;
	color: #a3a6aa;
	font-size: 0.75rem;
	font-weight: 500;
	direction: ltr;
	unicode-bidi: bidi-override
}

.chatlog__timestamp a {
	color: inherit
}

.chatlog__content {
	padding-right: 1rem;
	font-size: 0.95rem;
	word-wrap: break-word
}

.chatlog__edited-timestamp {
	margin-left: 0.15rem;
	color: #a3a6aa;
	font-size: 0.75rem;
	font-weight: 500
}

.chatlog__attachment {
	position: relative;
	width: fit-content;
	margin-top: 0.3rem;
	border-radius: 3px;
	overflow: hidden
}

.chatlog__attachment--hidden {
	cursor: pointer;
	box-shadow: 0 0 1px 1px rgba(0, 0, 0, 0.1)
}

.chatlog__attachment--hidden * {
	pointer-events: none
}

.chatlog__attachment-spoiler-caption {
	display: none;
	position: absolute;
	left: 50%;
	top: 50%;
	z-index: 999;
	padding: 0.4rem 0.8rem;
	border-radius: 20px;
	transform: translate(-50%, -50%);
	background-color: rgba(0, 0, 0, 0.9);
	color: #dcddde;
	font-size: 0.9rem;
	font-weight: 600;
	letter-spacing: 0.05rem
}

.chatlog__attachment--hidden .chatlog__attachment-spoiler-caption {
	display: block
}

.chatlog__attachment--hidden:hover .chatlog__attachment-spoiler-caption {
	color: #fff
}

.chatlog__attachment-media {
	max-width: 45vw;
	max-height: 500px;
	vertical-align: top;
	border-radius: 3px
}

.chatlog__attachment--hidden .chatlog__attachment-media {
	filter: blur(44px)
}

.chatlog__attachment-generic {
	max-width: 520px;
	width: 100%;
	height: 40px;
	padding: 10px;
	border: 1px solid #292b2f;
	border-radius: 3px;
	background-color: var(--panel-channels-bg);
	overflow: hidden
}

.chatlog__attachment--hidden .chatlog__attachment-generic {
	filter: blur(44px)
}

.chatlog__attachment-generic-icon {
	float: left;
	width: 30px;
	height: 100%;
	margin-right: 10px
}

.chatlog__attachment-generic-size {
	color: #72767d;
	font-size: 12px
}

.chatlog__attachment-generic-name {
	overflow: hidden;
	white-space: nowrap;
	text-overflow: ellipsis
}

.chatlog__embed {
	display: flex;
	margin-top: 0.3rem;
	max-width: 520px
}

.chatlog__embed-color-pill {
	flex-shrink: 0;
	width: 0.25rem;
	border-top-left-radius: 3px;
	border-bottom-left-radius: 3px
}

.chatlog__embed-color-pill--default {
	background-color: #202225
}

.chatlog__embed-content-container {
	display: flex;
	flex-direction: column;
	padding: 0.5rem 0.6rem;
	border: 1px solid rgba(46, 48, 54, 0.6);
	border-top-right-radius: 3px;
	border-bottom-right-radius: 3px;
	background-color: rgba(46, 48, 54, 0.3)
}

.chatlog__embed-content {
	display: flex;
	width: 100%
}

.chatlog__embed-text {
	flex: 1
}

.chatlog__embed-author-container {
	display: flex;
	margin-bottom: 0.5rem;
	align-items: center
}

.chatlog__embed-author-icon {
	width: 20px;
	height: 20px;
	margin-right: 0.5rem;
	border-radius: 50%
}

.chatlog__embed-author {
	color: #ffffff;
	font-size: 0.875rem;
	font-weight: 600;
	direction: ltr;
	unicode-bidi: bidi-override
}

.chatlog__embed-author-link {
	color: #ffffff
}

.chatlog__embed-title {
	margin-bottom: 0.5rem;
	color: #ffffff;
	font-size: 0.875rem;
	font-weight: 600
}

.chatlog__embed-description {
	color: #dcddde;
	font-weight: 500;
	font-size: 0.85rem
}

.chatlog__embed-fields {
	display: flex;
	flex-wrap: wrap;
	gap: 0 0.5rem
}

.chatlog__embed-field {
	flex: 0;
	min-width: 100%;
	max-width: 506px;
	padding-top: 0.6rem;
	font-size: 0.875rem
}

.chatlog__embed-field--inline {
	flex: 1;
	flex-basis: auto;
	min-width: 50px
}

.chatlog__embed-field-name {
	margin-bottom: 0.2rem;
	color: #ffffff;
	font-weight: 600
}

.chatlog__embed-field-value {
	color: #dcddde;
	font-weight: 500
}


.chatlog__embed-images {
	display: grid;
	margin-top: 0.6rem;
	grid-template-columns: repeat(2, 1fr);
	gap: 0.25rem
}

.chatlog__embed-images--single {
	display: block
}

.chatlog__embed-image {
	object-fit: cover;
	object-position: center;
	max-width: 500px;
	max-height: 400px;
	width: 100%;
	height: 100%;
	border-radius: 3px
}

.chatlog__embed-footer {
	margin-top: 0.6rem;
	color: #dcddde
}

.chatlog__embed-footer-icon {
	width: 20px;
	height: 20px;
	margin-right: 0.2rem;
	border-radius: 50%;
	vertical-align: middle
}

.chatlog__embed-footer-text {
	vertical-align: middle;
	font-size: 0.75rem;
	font-weight: 500
}

.chatlog__embed-generic-image {
	max-width: 45vw;
	max-height: 500px;
	vertical-align: top;
	border-radius: 3px
}

.chatlog__embed-generic-gifv {
	max-width: 45vw;
	max-height: 500px;
	vertical-align: top;
	border-radius: 3px
}

.chatlog__embed-spotify {
	border: 0
}

.chatlog__embed-youtube-container {
	margin-top: 0.6rem
}

.chatlog__embed-youtube {
	border: 0;
	border-radius: 3px
}

.chatlog__sticker {
	width: 180px;
	height: 180px
}

.chatlog__sticker--media {
	max-width: 100%;
	max-height: 100%
}

.chatlog__reactions {
	display: flex
}

.chatlog__reaction {
	display: flex;
	margin: 0.35rem 0.1rem 0.1rem 0;
	padding: 0.125rem 0.375rem;
	border: 1px solid transparent;
	border-radius: 8px;
	background-color: var(--panel-channels-bg);
	align-items: center
}

.chatlog__reaction:hover {
	border: 1px solid hsla(0, 0%, 100%, .2);
	background-color: transparent
}

.chatlog__reaction-count {
	min-width: 9px;
	margin-left: 0.35rem;
	color: #b9bbbe;
	font-size: 0.875rem
}

.chatlog__reaction:hover .chatlog__reaction-count {
	color: #dcddde
}

.chatlog__markdown {
	max-width: 100%;
	line-height: 1.3;
	overflow-wrap: break-word
}

.chatlog__markdown-preserve {
	white-space: pre-wrap
}

.chatlog__markdown-spoiler {
	background-color: rgba(255, 255, 255, 0.1);
	border-radius: 3px
}

.chatlog__markdown-spoiler--hidden {
	cursor: pointer;
	background-color: #202225;
	color: rgba(0, 0, 0, 0)
}

.chatlog__markdown-spoiler--hidden:hover {
	background-color: rgba(32, 34, 37, 0.8)
}

.chatlog__markdown-spoiler--hidden::selection {
	color: rgba(0, 0, 0, 0)
}

.chatlog__markdown-quote {
	display: flex;
	margin: 0.05rem 0
}

.chatlog__embed-thumbnail {
	flex: 0;
	max-width: 80px;
	max-height: 80px;
	margin-left: 1.2rem;
	border-radius: 3px;
}

.chatlog__markdown-quote-border {
	margin-right: 0.5rem;
	border: 2px solid var(--borders2);
	border-radius: 3px
}

.chatlog__markdown-pre {
	background-color: var(--panel-channels-bg);
	font-family: "Consolas", "Courier New", Courier, monospace;
	font-size: 0.85rem
}

.chatlog__markdown-pre--multiline {
	display: block;
	margin-top: 0.25rem;
	padding: 0.5rem;
	border: 2px solid #282b30;
	border-radius: 5px;
	color: #b9bbbe
}

.chatlog__markdown-pre--multiline.hljs {
	background-color: var(--panel-channels-bg);
	color: #b9bbbe
}

.chatlog__markdown-pre--inline {
	display: inline-block;
	padding: 2px;
	border-radius: 3px
}

.chatlog__markdown-mention {
	border-radius: 3px;
	padding: 0 2px;
	background-color: rgba(88, 101, 242, .3);
	color: #dee0fc;
	font-weight: 500
}

.chatlog__markdown-mention:hover {
	background-color: #5865f2;
	color: #ffffff
}

.chatlog__markdown-timestamp {
	border-radius: 3px;
	padding: 0 2px;
	color: #a3a6aa
}

.chatlog__emoji {
	width: 1.325rem;
	height: 1.325rem;
	margin: 0 0.06rem;
	vertical-align: -0.4rem
}

.chatlog__emoji--small {
	width: 1rem;
	height: 1rem
}

.chatlog__emoji--large {
	width: 2.8rem;
	height: 2.8rem
}

.postamble {
	padding: 1.25rem
}

.postamble__entry {
	color: #ffffff
}


.chatlog__attachment-media {
	max-width: 45vw;
	max-height: 500px;
	vertical-align: top;
	border-radius: 3px;
}

.chatlog__attachment--hidden .chatlog__attachment-media {
	filter: blur(44px);
}



/* thin dark scrollbar */
::-webkit-scrollbar {
	width: 10px;
	height: 3px;
}

::-webkit-scrollbar-track {
	background-color: var(--panel-channels-bg);
}

::-webkit-scrollbar-track-piece {
	background-color: #2F3136;
}

::-webkit-scrollbar-thumb {
	height: 50px;
	background-color: #202225;
	border-radius: 3px;
}

::-webkit-scrollbar-corner {
	background-color: #646464;
}

::-webkit-resizer {
	background-color: #666;
}


.txt {
	font-size: 32px;
	padding-top: 20px;
	padding-left: 20px;
}
    """

pattern_ggsans = re.compile(r'(ggsans)-(italic|normal)-(400|500|600|700|800)')
pattern_whitney = re.compile(r'(whitney)-(300|400|500|600|700)')

style_css_temp = style_css

matches_ggsans = pattern_ggsans.findall(style_css)
for match in matches_ggsans:
    style_css_temp = style_css.replace(f'{match[0]}-{match[1]}-{match[2]}',f'https://raw.githubusercontent.com/jsmsj/DCE-JSONtoHTML/master/fonts/{match[0]}-{match[1]}-{match[2]}.woff2')

matches_whitney = pattern_whitney.findall(style_css)
for match in matches_whitney:
    style_css_temp = style_css_temp.replace(f'{match[0]}-{match[1]}',f'https://raw.githubusercontent.com/jsmsj/DCE-JSONtoHTML/master/fonts/{match[0]}-{match[1]}.woff')


style_css = style_css_temp

with open(f'InputFiles/{name_of_file_to_load}.html','w') as m:
    m.write("""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document</title>
    """)
    m.write(f'<style>{style_css}</style>')
    del style_css
    m.write("""
    <link rel=stylesheet href=https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.15.6/styles/solarized-dark.min.css>
    <script src=https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.15.6/highlight.min.js></script>
    <script>document.addEventListener('DOMContentLoaded', () => { document.querySelectorAll('.chatlog__markdown-pre--multiline').forEach(e => hljs.highlightBlock(e)); });</script>
    <script src=https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.8.1/lottie.min.js></script>
    <script>document.addEventListener('DOMContentLoaded', () => { document.querySelectorAll('.chatlog__sticker--media[data-source]').forEach(e => { const anim = lottie.loadAnimation({ container: e, renderer: 'svg', loop: true, autoplay: true, path: e.getAttribute('data-source') }); anim.addEventListener('data_failed', () => e.innerHTML = '<strong>[Sticker cannot be rendered]</strong>'); }); });</script>
    <script>function scrollToMessage(event, id) {
            const element = document.getElementById('chatlog__message-container-' + id); if (!element)
                return; event.preventDefault(); element.classList.add('chatlog__message-container--highlighted'); window.scrollTo({ top: element.getBoundingClientRect().top - document.body.getBoundingClientRect().top - (window.innerHeight / 2), behavior: 'smooth' }); window.setTimeout(() => element.classList.remove('chatlog__message-container--highlighted'), 2000);
        }
        function showSpoiler(event, element) {
            if (!element)
                return; if (element.classList.contains('chatlog__attachment--hidden')) { event.preventDefault(); element.classList.remove('chatlog__attachment--hidden'); }
            if (element.classList.contains('chatlog__markdown-spoiler--hidden')) { event.preventDefault(); element.classList.remove('chatlog__markdown-spoiler--hidden'); }
        }
    </script>

</head>
<body>
    <svg style=display:none xmlns=http://www.w3.org/2000/svg>
        <defs>
            <symbol id=attachment-icon viewBox="0 0 720 960">
                <path fill=#f4f5fb
                    d=M50,935a25,25,0,0,1-25-25V50A25,25,0,0,1,50,25H519.6L695,201.32V910a25,25,0,0,1-25,25Z />
                <path fill=#7789c4
                    d=M509.21,50,670,211.63V910H50V50H509.21M530,0H50A50,50,0,0,0,0,50V910a50,50,0,0,0,50,50H670a50,50,0,0,0,50-50h0V191Z />
                <path fill=#f4f5fb
                    d=M530,215a25,25,0,0,1-25-25V50a25,25,0,0,1,16.23-23.41L693.41,198.77A25,25,0,0,1,670,215Z />
                <path fill=#7789c4
                    d=M530,70.71,649.29,190H530V70.71M530,0a50,50,0,0,0-50,50V190a50,50,0,0,0,50,50H670a50,50,0,0,0,50-50Z />
            </symbol>
            <symbol id=channel-pinned-message-icon viewBox="0 0 18 18">
                <path fill=#b9bbbe
                    d="m16.908 8.39684-8.29587-8.295827-1.18584 1.184157 1.18584 1.18584-4.14834 4.1475v.00167l-1.18583-1.18583-1.185 1.18583 3.55583 3.55502-4.740831 4.74 1.185001 1.185 4.74083-4.74 3.55581 3.555 1.185-1.185-1.185-1.185 4.1475-4.14836h.0009l1.185 1.185z" />
            </symbol>
            <symbol id=call-icon viewBox="0 0 18 18">
                <path fill=#3ba55c fill-rule=evenodd
                    d="M17.7163041 15.36645368c-.0190957.02699568-1.9039523 2.6680735-2.9957762 2.63320406-3.0676659-.09785935-6.6733809-3.07188394-9.15694343-5.548738C3.08002193 9.9740657.09772497 6.3791404 0 3.3061316v-.024746C0 2.2060575 2.61386252.3152347 2.64082114.2972376c.7110335-.4971705 1.4917101-.3149497 1.80959713.1372281.19320342.2744561 2.19712724 3.2811005 2.42290565 3.6489167.09884826.1608492.14714912.3554431.14714912.5702838 0 .2744561-.07975258.5770327-.23701117.8751101-.1527655.2902036-.65262318 1.1664385-.89862055 1.594995.2673396.3768148.94804468 1.26429792 2.351016 2.66357424 1.39173858 1.39027775 2.28923588 2.07641807 2.67002628 2.34187563.4302146-.2452108 1.3086162-.74238132 1.5972981-.89423205.5447887-.28682915 1.0907006-.31944893 1.4568885-.08661115.3459689.2182151 3.3383754 2.21027167 3.6225641 2.41611376.2695862.19234426.4144887.5399137.4144887.91672846 0 .2969525-.089862.61190215-.2808189.88523346" />
            </symbol>
            <symbol id=guild-member-join-icon viewBox="0 0 18 18">
                <path fill=#3ba55c d="m0 8h14.2l-3.6-3.6 1.4-1.4 6 6-6 6-1.4-1.4 3.6-3.6h-14.2" />
            </symbol>
        </defs>
    </svg>
""")
    m.write(f"""
     <div class=preamble>
        <div class=preamble__guild-icon-container><img class=preamble__guild-icon
                src="{guild_iconurl}"
                alt="Guild icon" loading=lazy
                height="200px"
                width="200px">
            </img></div>
        <div class=preamble__entries-container>
            <div class=preamble__entry>{guild_name}</div>
            <div class=preamble__entry>{channel_category} / {channel_name}</div>
            <div class="preamble__entry preamble__entry--small">{channel_name}</div>
        </div>
    </div>
    <div class="chatlog">
""")
    print(f'Converting {name_of_file_to_load} to HTML. Please Wait.....')
    for m_index,message in enumerate(messages):
        m.write(f"""
<div id="chatlog__message-container-{message['id']}" class="chatlog__message-container {"chatlog__message-container--pinned" if message['isPinned'] else ''}" data-message-id="{message['id']}">
    <div class="chatlog__message">    
        {handle_system_message(message) if message['type'].lower() in system_message_types else handle_message(message,m_index if m_index == 0 else None)}
    </div>
</div>
""")
        printProgressBar(m_index+1, total_messages, prefix ='Progress:', suffix = 'Complete', length = 50)
        
    m.write('\n</div>\n</body>\n</html>')