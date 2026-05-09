import json
import os
from loguru import logger
from apis.xhs_pc_apis import XHS_Apis
from xhs_utils.common_util import init
from xhs_utils.data_util import handle_note_info, download_note, save_to_xlsx, timestamp_to_str


SAVE_CHOICES = {'none', 'all', 'media', 'media-image', 'media-video', 'excel'}


class Data_Spider():
    def __init__(self):
        self.xhs_apis = XHS_Apis()

    def _build_note_url(self, note: dict) -> str:
        note_card = note.get('note_card') if isinstance(note.get('note_card'), dict) else {}
        note_id = note.get('id') or note.get('note_id') or note_card.get('id') or note_card.get('note_id')
        if not note_id:
            return ''

        query_parts = []
        xsec_token = note.get('xsec_token') or note.get('xsecToken') or note_card.get('xsec_token')
        xsec_source = note.get('xsec_source') or note.get('xsecSource') or note_card.get('xsec_source')
        if xsec_token:
            query_parts.append(f"xsec_token={xsec_token}")
        if xsec_source:
            query_parts.append(f"xsec_source={xsec_source}")

        note_url = f"https://www.xiaohongshu.com/explore/{note_id}"
        if query_parts:
            note_url = f"{note_url}?{'&'.join(query_parts)}"
        return note_url

    def _is_note_item(self, item: dict) -> bool:
        if not isinstance(item, dict):
            return False
        if item.get('model_type') == 'note':
            return True
        note_card = item.get('note_card')
        return isinstance(note_card, dict) and bool(
            item.get('id') or item.get('note_id') or note_card.get('id') or note_card.get('note_id')
        )

    def _extract_image_url(self, image) -> str:
        if isinstance(image, str):
            return image
        if not isinstance(image, dict):
            return ''

        info_list = image.get('info_list')
        if isinstance(info_list, list):
            for image_info in reversed(info_list):
                if isinstance(image_info, dict) and image_info.get('url'):
                    return image_info['url']

        for key in ('url_default', 'url_pre', 'url', 'src'):
            if image.get(key):
                return image[key]
        return ''

    def _normalize_search_note(self, note: dict, note_url: str = '') -> dict:
        note_card = note.get('note_card') if isinstance(note.get('note_card'), dict) else note
        user_info = note_card.get('user') if isinstance(note_card.get('user'), dict) else {}
        interact_info = note_card.get('interact_info') if isinstance(note_card.get('interact_info'), dict) else {}

        note_id = note.get('id') or note.get('note_id') or note_card.get('id') or note_card.get('note_id') or ''
        note_type_raw = note_card.get('type') or note.get('note_type') or 'normal'
        note_type = '视频' if note_type_raw in {'video', '视频'} else '图集'
        normalized_url = note_url or self._build_note_url(note)

        image_list = []
        for image in note_card.get('image_list') or note.get('image_list') or []:
            image_url = self._extract_image_url(image)
            if image_url and image_url not in image_list:
                image_list.append(image_url)

        cover_url = self._extract_image_url(note_card.get('cover') or note.get('cover'))
        if cover_url and cover_url not in image_list:
            image_list.append(cover_url)

        tags = []
        for tag in note_card.get('tag_list') or note.get('tag_list') or []:
            if isinstance(tag, dict) and tag.get('name'):
                tags.append(tag['name'])

        upload_time = ''
        raw_time = note_card.get('time') or note.get('time')
        if raw_time:
            try:
                upload_time = timestamp_to_str(int(raw_time))
            except (TypeError, ValueError):
                upload_time = str(raw_time)

        title = note_card.get('title') or note_card.get('display_title') or note.get('title') or '无标题'
        desc = note_card.get('desc') or note.get('desc') or note_card.get('display_title') or ''
        liked_count = interact_info.get('liked_count') or note.get('liked_count') or note.get('likes') or 0

        return {
            'note_id': note_id,
            'note_url': normalized_url,
            'note_type': note_type,
            'user_id': user_info.get('user_id') or user_info.get('id') or note.get('user_id') or '',
            'home_url': f"https://www.xiaohongshu.com/user/profile/{user_info.get('user_id') or user_info.get('id') or note.get('user_id') or ''}",
            'nickname': user_info.get('nickname') or user_info.get('nick_name') or note.get('nickname') or '未知用户',
            'avatar': user_info.get('avatar') or user_info.get('image') or note.get('avatar') or '',
            'title': title.strip() or '无标题',
            'desc': desc,
            'liked_count': liked_count,
            'collected_count': interact_info.get('collected_count') or note.get('collected_count') or 0,
            'comment_count': interact_info.get('comment_count') or note.get('comment_count') or 0,
            'share_count': interact_info.get('share_count') or note.get('share_count') or 0,
            'video_cover': image_list[0] if note_type == '视频' and image_list else None,
            'video_addr': note.get('video_addr') or None,
            'image_list': image_list,
            'tags': tags,
            'upload_time': upload_time,
            'ip_location': note_card.get('ip_location') or note.get('ip_location') or '未知',
        }

    def spider_note(self, note_url: str, cookies_str: str, proxies=None):
        """
        爬取一个笔记的信息
        :param note_url:
        :param cookies_str:
        :return:
        """
        note_info = None
        try:
            success, msg, note_info = self.xhs_apis.get_note_info(note_url, cookies_str, proxies)
            if success:
                data = note_info.get('data') if isinstance(note_info, dict) else {}
                items = data.get('items') if isinstance(data, dict) else None
                if isinstance(items, dict):
                    items = [items]
                if not items:
                    raise KeyError('data.items')
                note_info = items[0]
                note_info['url'] = note_url
                note_info = handle_note_info(note_info)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'爬取笔记信息 {note_url}: {success}, msg: {msg}')
        return success, msg, note_info

    def spider_some_note(self, notes: list, cookies_str: str, base_path: dict, save_choice: str, excel_name: str = '', proxies=None, fallback_notes: list | None = None):
        """
        爬取一些笔记的信息，并按 save_choice 保存媒体/Excel。

        兼容说明：
        - 旧版 Spider_XHS 主要负责下载媒体和保存 Excel；
        - 项目接入后需要把 note_list 返回给业务层入库；
        - 当前后端导入主流程使用 save_choice='none'，只返回数据给数据库层，不落本地文件；
        - 详情接口失效时，可传入 fallback_notes，用搜索结果卡片兜底入库。
        """
        if save_choice not in SAVE_CHOICES:
            raise ValueError(f"save_choice 仅支持: {', '.join(sorted(SAVE_CHOICES))}")
        if (save_choice == 'all' or save_choice == 'excel') and excel_name == '':
            raise ValueError('excel_name 不能为空')
        
        note_list = []
        fallback_notes = fallback_notes or []
        for index, note_url in enumerate(notes):
            success, msg, note_info = self.spider_note(note_url, cookies_str, proxies)
            if (not success or note_info is None) and index < len(fallback_notes):
                fallback_note = fallback_notes[index]
                if fallback_note:
                    note_info = self._normalize_search_note(fallback_note, note_url)
                    logger.warning(f"笔记详情接口失败，已使用搜索结果兜底 note_url={note_url}, msg={msg}")
            if note_info is not None:
                note_list.append(note_info)
        
        if save_choice in ['all', 'media', 'media-image', 'media-video']:
            media_path = base_path.get('media') if isinstance(base_path, dict) else None
            if not media_path:
                raise ValueError("base_path 缺少 media 保存路径")
            os.makedirs(media_path, exist_ok=True)
            for note_info in note_list:
                try:
                    download_note(note_info, media_path, save_choice)
                except Exception as exc:
                    logger.warning(f"下载笔记媒体失败 note_id={note_info.get('note_id')}: {exc}")

        if save_choice in ['all', 'excel']:
            excel_path = base_path.get('excel') if isinstance(base_path, dict) else None
            if not excel_path:
                raise ValueError("base_path 缺少 excel 保存路径")
            os.makedirs(excel_path, exist_ok=True)
            save_to_xlsx(note_list, os.path.join(excel_path, f'{excel_name}.xlsx'), 'note')

        return note_list

    def spider_user_all_note(self, user_url: str, cookies_str: str, base_path: dict, save_choice: str, excel_name: str = '', proxies=None):
        """
        爬取一个用户的所有笔记
        :param user_url:
        :param cookies_str:
        :param base_path:
        :return:
        """
        note_list = []
        try:
            success, msg, all_note_info = self.xhs_apis.get_user_all_notes(user_url, cookies_str, proxies)
            if success:
                logger.info(f'用户 {user_url} 作品数量: {len(all_note_info)}')
                for simple_note_info in all_note_info:
                    note_url = f"https://www.xiaohongshu.com/explore/{simple_note_info['note_id']}?xsec_token={simple_note_info['xsec_token']}"
                    note_list.append(note_url)
            if save_choice == 'all' or save_choice == 'excel':
                excel_name = user_url.split('/')[-1].split('?')[0]
            self.spider_some_note(note_list, cookies_str, base_path, save_choice, excel_name, proxies)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'爬取用户所有视频 {user_url}: {success}, msg: {msg}')
        return note_list, success, msg

    def spider_some_search_note(self, query: str, require_num: int, cookies_str: str, base_path: dict, save_choice: str, sort_type_choice=0, note_type=0, note_time=0, note_range=0, pos_distance=0, geo: dict = None,  excel_name: str = '', proxies=None):
        """
        搜索笔记 (已修改：返回详细数据列表)
        """
        result_data = [] # 用于存储最终结果
        note_urls = []
        notes = []
        try:
            success, msg, notes = self.xhs_apis.search_some_note(query, require_num, cookies_str, sort_type_choice, note_type, note_time, note_range, pos_distance, geo, proxies)
            if success:
                notes = [note for note in notes if self._is_note_item(note)]
                logger.info(f'搜索关键词 {query} 笔记数量: {len(notes)}')
            
            if save_choice == 'all' or save_choice == 'excel':
                excel_name = query
            
            # ✅ 修改：接收 spider_some_note 返回的数据
            fallback_notes = []
            for note in notes:
                note_url = self._build_note_url(note)
                if not note_url:
                    logger.warning(f"搜索结果缺少 note_id，已跳过: {note}")
                    continue
                note_urls.append(note_url)
                fallback_notes.append(note)

            result_data = self.spider_some_note(
                note_urls,
                cookies_str,
                base_path,
                save_choice,
                excel_name,
                proxies,
                fallback_notes=fallback_notes,
            )
            
        except Exception as e:
            success = False
            msg = e
        logger.info(f'搜索关键词 {query} 笔记: {success}, msg: {msg}')
        
        # ✅ 修改：返回 result_data (包含详细内容的字典列表)
        return result_data, success, msg

if __name__ == '__main__':
    """
        此文件为爬虫的入口文件，可以直接运行
        apis/xhs_pc_apis.py 为爬虫的api文件，包含小红书的全部数据接口，可以继续封装
        apis/xhs_creator_apis.py 为小红书创作者中心的api文件
        感谢star和follow
    """

    cookies_str, base_path = init()
    data_spider = Data_Spider()
    """
        save_choice: all: 保存所有的信息, media: 保存视频和图片（media-video只下载视频, media-image只下载图片，media都下载）, excel: 保存到excel
        save_choice 为 excel 或者 all 时，excel_name 不能为空
    """


    # 1 爬取列表的所有笔记信息 笔记链接 如下所示 注意此url会过期！
    notes = [
        r'https://www.xiaohongshu.com/explore/683fe17f0000000023017c6a?xsec_token=ABBr_cMzallQeLyKSRdPk9fwzA0torkbT_ubuQP1ayvKA=&xsec_source=pc_user',
    ]
    data_spider.spider_some_note(notes, cookies_str, base_path, 'all', 'test')

    # 2 爬取用户的所有笔记信息 用户链接 如下所示 注意此url会过期！
    user_url = 'https://www.xiaohongshu.com/user/profile/64c3f392000000002b009e45?xsec_token=AB-GhAToFu07JwNk_AMICHnp7bSTjVz2beVIDBwSyPwvM=&xsec_source=pc_feed'
    data_spider.spider_user_all_note(user_url, cookies_str, base_path, 'all')

    # 3 搜索指定关键词的笔记
    query = "榴莲"
    query_num = 10
    sort_type_choice = 0  # 0 综合排序, 1 最新, 2 最多点赞, 3 最多评论, 4 最多收藏
    note_type = 0 # 0 不限, 1 视频笔记, 2 普通笔记
    note_time = 0  # 0 不限, 1 一天内, 2 一周内天, 3 半年内
    note_range = 0  # 0 不限, 1 已看过, 2 未看过, 3 已关注
    pos_distance = 0  # 0 不限, 1 同城, 2 附近 指定这个1或2必须要指定 geo
    # geo = {
    #     # 经纬度
    #     "latitude": 39.9725,
    #     "longitude": 116.4207
    # }
    data_spider.spider_some_search_note(query, query_num, cookies_str, base_path, 'all', sort_type_choice, note_type, note_time, note_range, pos_distance, geo=None)
