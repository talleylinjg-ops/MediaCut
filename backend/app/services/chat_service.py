import base64
import json
import os
import re
import uuid

import httpx

from app.core import channels
from app.core.settings import get_modelscope_token
from app.services import ai_service, audio_service, image_service, video_service

MODELSCOPE_CHAT_URL = "https://api-inference.modelscope.cn/v1/chat/completions"
CHAT_MODEL = "Qwen/Qwen3.5-35B-A3B"
QWEN_VL_MODEL = "Qwen/Qwen3-VL-8B-Instruct"

SYSTEM_PROMPT = (
    "你是媒体剪辑助手，根据用户请求和输入媒体类型决定执行动作。"
    "只输出一个 JSON 对象，不要输出任何其他文字。JSON 结构："
    '{"action":"image_understand|image_edit|i2i|audio_edit|matting|enhance|asr|tts|image_to_video|t2i|reply","params":{},"reply":"给用户的简短中文回复"}。'
    "图片输入时 action 可选 image_understand/image_edit/i2i/matting/enhance/image_to_video，"
    "若用户是在询问图片内容（如：这是什么/图里有什么/描述一下/识别图中文字/帮我看看），action 必须用 image_understand，params 留空，reply 简短说明已识别。"
    "图片编辑 params 支持 filter(gray/blur/sharpen/edge/emboss/cinematic/invert/sepia/warm/cool/pixelate/vignette/contrast/sketch/cartoon/flip)、resize(width)、watermark(text,size,position)、crop、output_format(png/jpeg/webp)。"
    "watermark.position 可为 'center'/'top-left'/'top-right'/'bottom-left'/'bottom-right' 或 [x,y] 坐标。"
    "image_to_video params 支持 duration(秒)、motion(zoom/pan)，基于已上传图片生成镜头运镜视频：zoom 为缓慢推进，pan 为横向平移（适合驰骋/行驶/公路等有方向感的表达）。注意：这只是镜头推拉/平移，画面内容本身不会运动。"
    "i2i 为基于已上传图片的云端生成式修改：当用户对图中内容提出修改（如把衣服换成红色/换风格/加一顶帽子/去掉背景里的路人/背景换成海边/改成动漫风/加一轮月亮/给画面添加文字等），action 用 i2i，params 写 {\"prompt\":\"对图片的完整、具体的修改要求，保留原图主体与构图\"}。"
    "注意区分：需要保持尺寸与像素可逆加工（滤镜/灰度/水印/裁剪/缩放/转格式/抠图/增强）用 image_edit/matting/enhance；对内容做生成式改写（换装/加删物体/改背景/风格化重绘/叠加画面元素）用 i2i；两者不要混淆。"
    "音频输入时 action 可选 audio_edit/asr，"
    "音频编辑 params 支持 crop(start,end)、volume(gain)、output_format(mp3/wav/aac)。"
    "只有文字时可用 reply 直接回答，或用 tts 将文字转为语音。"
    "重要：只要用户上传了图片并提出视频/动画/动态相关请求（如：生成视频、做成动态、动起来、驰骋、飞驰、行驶、平移运镜），action 一律用 image_to_video（可带图自动生成运镜），绝对不要用 reply 拒绝或误判为图片内容修改。reply 只需简短告知正在生成视频。"
    "文生图：仅当用户没有上传图片、且明确要求生成一张全新的图（例如：生成一张/画一张/帮我画/设计 logo/海报/封面/插画/头像/壁纸/背景图，或描述一个不存在于任何素材的画面）时，action 用 t2i，params 写 {\"prompt\":\"保留用户主体、风格、构图、画面细节的完整生成描述\"}。"
    "当输入中包含『图片内容：』字段时，它是对用户上传图片的视觉理解结果，你应该基于图片实际内容理解用户意图并选择最合适的动作（例如图片是人物照片且用户要复古风格，就执行 sepia 复古滤镜；用户询问图中人物外貌则用 image_understand 回答）。"
    "对于已上传图片的内容级修改（换装、换脸、添加/删除物体、换背景、改变画风、季节光影等生成式需求），action 用 i2i 执行云端生成式修改，不要用 reply 拒绝。"
    "目前唯一做不到的是让已上传图片的画面内容真正运动（如让车开起来、让动作发生）：这类视频生成请求按第上一条执行 image_to_video 运镜视频即可，并在 reply 中如实说明这只是镜头运镜。"
    "若用户没有上传图片且直接提出生成/换装/凭空绘制需求，一律使用 t2i 生成全新图片，不要使用 reply 拒绝。"
)


def _image_mime(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }.get(ext, "image/png")


def _image_caption(image_path: str) -> str | None:
    token = get_modelscope_token()
    if not token or not os.path.exists(image_path):
        return None
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        payload = {
            "model": QWEN_VL_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{_image_mime(image_path)};base64,{b64}"}},
                        {
                            "type": "text",
                            "text": "请用一两句中文简洁描述这张图片的内容：主体、场景、人物外貌、画面色彩等，若有清晰文字请一并念出，控制在60字内。",
                        },
                    ],
                }
            ],
            "temperature": 0.2,
            "max_tokens": 300,
        }
        resp = httpx.post(
            MODELSCOPE_CHAT_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=90,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()[:300]
    except Exception:
        return None


def _channel_chat(channel: dict, messages: list[dict]) -> str:
    base = channel["base_url"].rstrip("/")
    headers = {}
    if channel.get("api_key"):
        headers["Authorization"] = f"Bearer {channel['api_key']}"
    payload = {
        "model": channel.get("model_id") or "",
        "messages": messages,
        "temperature": 0.2,
    }
    resp = httpx.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=90)
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("unexpected channel response")


def chat_completion(messages: list[dict]) -> str:
    for channel in channels.resolve("chat"):
        try:
            return _channel_chat(channel, messages)
        except Exception:
            continue
    token = get_modelscope_token()
    if not token:
        raise RuntimeError("MODELSCOPE_API_TOKEN not configured")
    payload = {
        "model": CHAT_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    resp = httpx.post(
        MODELSCOPE_CHAT_URL,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=90,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("unexpected LLM response")


def parse_with_llm(text: str, media_kind: str, caption: str | None = None) -> dict | None:
    user = f"用户请求：{text}\n输入媒体类型：{media_kind or '无'}"
    if caption:
        user = f"图片内容：{caption}\n{user}"
    try:
        content = chat_completion([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}])
    except Exception:
        return None
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None
    try:
        intent = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    action = intent.get("action")
    if action not in (
        "image_understand",
        "image_edit",
        "i2i",
        "audio_edit",
        "matting",
        "enhance",
        "asr",
        "tts",
        "image_to_video",
        "t2i",
        "reply",
    ):
        return None
    params = intent.get("params") or {}
    return {"action": action, "params": params, "reply": intent.get("reply", "")}


def parse_with_rules(text: str, media_kind: str) -> dict:
    t = text.strip()
    reply = ""
    if media_kind == "image":
        if re.search(
            r"这是什么|那是什么|图里(有|是|有什)|图片里(有|是)|图中(有|是|是什)|上面(是|有|画)|"
            r"描述|介绍一下|帮我看看|看看这张|这张图是|图片内容|识别|认识一下|讲一讲|帮我分析",
            t,
        ):
            return {"action": "image_understand", "params": {}, "reply": "已识别图片内容"}
        if re.search(r"视频|动画|动图|动起来|动态|飞驰|驰骋|行驶|漂移|平移|运镜|推镜|拉远|放大效果", t):
            m = re.search(r"(\d+)\s*秒", t)
            duration = int(m.group(1)) if m else 5
            params = {"duration": duration}
            if re.search(r"驰骋|行驶|平移|横向|扫过|公路|拉风|飞驰|移动", t):
                params["motion"] = "pan"
            return {
                "action": "image_to_video",
                "params": params,
                "reply": f"正在基于图片生成 {duration} 秒镜头运镜视频",
            }
        params = {}
        if re.search(r"灰度|黑白", t):
            params["filter"] = "gray"
        elif "模糊" in t:
            params["filter"] = "blur"
        elif "锐化" in t:
            params["filter"] = "sharpen"
        elif "边缘" in t:
            params["filter"] = "edge"
        elif "浮雕" in t:
            params["filter"] = "emboss"
        elif re.search(r"大片|电影|原色|调色|色调|质感|滤镜", t):
            params["filter"] = "cinematic"
        elif re.search(r"反色|负片|底片", t):
            params["filter"] = "invert"
        elif re.search(r"素描|铅笔画|手绘", t):
            params["filter"] = "sketch"
        elif re.search(r"复古|怀旧|棕褐|老照片|旧照片", t):
            params["filter"] = "sepia"
        elif re.search(r"暖色|暖调|暖光", t):
            params["filter"] = "warm"
        elif re.search(r"冷色|冷调", t):
            params["filter"] = "cool"
        elif re.search(r"马赛克|像素化", t):
            params["filter"] = "pixelate"
        elif "暗角" in t:
            params["filter"] = "vignette"
        elif re.search(r"高对比|增强对比|对比度", t):
            params["filter"] = "contrast"
        elif re.search(r"卡通|漫画|动漫化", t):
            params["filter"] = "cartoon"
        elif re.search(r"镜像|翻转|左右翻转", t):
            params["filter"] = "flip"
        m = re.search(r"(放大|缩小)", t)
        if m:
            ratio = 2.0 if m.group(1) == "放大" else 0.5
            params.setdefault("resize", {"width": 0, "height": 0})
        if re.search(r"logo|水印|加字|加文字|打上|加上|电话号码|手机号", t, re.IGNORECASE):
            wm_text = None
            lm = re.search(r"logo\s*([A-Za-z0-9]+)", t, re.IGNORECASE)
            if lm:
                wm_text = lm.group(1)
            else:
                m = re.search(r"(?:水印|加字|加文字)\s*[:：]?\s*([A-Za-z0-9\u4e00-\u9fff]+)", t)
                if m:
                    wm_text = m.group(1)
            if not wm_text:
                m = re.search(r"(?:电话号码|手机号|电话|号码)\s*[:：]?\s*([0-9]{5,})", t)
                if m:
                    wm_text = m.group(1)
            wm = {"text": wm_text or "MediaCut", "size": 36}
            if "右上" in t:
                wm["position"] = "top-right"
            elif "右下" in t:
                wm["position"] = "bottom-right"
            elif "左下" in t:
                wm["position"] = "bottom-left"
            elif "左上" in t:
                wm["position"] = "top-left"
            elif "中间" in t or "居中" in t:
                wm["position"] = "center"
            params.setdefault("watermark", wm)
        for fmt in ("png", "jpeg", "webp"):
            if f"转{fmt}" in t or fmt in t:
                params.setdefault("output_format", fmt)
        if "抠图" in t:
            return {"action": "matting", "params": {}, "reply": "开始人像抠图"}
        if "增强" in t:
            return {"action": "enhance", "params": {}, "reply": "开始画质增强"}
        if params:
            return {"action": "image_edit", "params": params, "reply": "已按你的要求处理图片"}
        if re.search(
            r"换(装|衣|衣服)|衣服换成|服装换成|发型换成|发色换成|头发换成|肤色换成|换脸|"
            r"穿.{0,8}(衣服|西装|裙|外套|大衣|衬衫|T恤)|"
            r"加.{0,6}(帽子|眼镜|墨镜|项链|耳环|纹身|胡须|胡子|刘海|围巾|领带|头饰|皇冠|蕾丝|蝴蝶结|花边|装饰|披肩)|"
            r"给.{0,8}(添加|戴上|穿上|加上|换成)|摘(掉|下)|去掉|删(掉|除)|移除|消除|"
            r"(染成|涂成|改成|换成).{0,6}色|改成.{0,4}款|(改|换)(个|下|一下)?颜色|颜色改|颜色换|"
            r"背景换成|背景改成|改成(动漫|卡通|油画|水墨|赛博朋克|夜景|雪景|漫画|古风)|变成.{0,6}(风|风格)|"
            r"加.{0,6}(月亮|太阳|云|彩虹|花|雪|烟花)|增(加|添)",
            t,
        ):
            return {
                "action": "i2i",
                "params": {"prompt": t},
                "reply": "正在基于原图生成修改效果，需要十几秒到一分钟，请稍候",
            }
        return {"action": "reply", "params": {}, "reply": "请告诉我具体要做什么，例如：加水印、转png、灰度、放大、抠图、增强。"}
    if media_kind == "audio":
        params = {}
        m = re.search(r"从\s*([\d.]+)\s*秒到\s*([\d.]+)\s*秒", t) or re.search(r"裁剪?\s*([\d.]+)\s*[-到至~]\s*([\d.]+)", t)
        if m:
            params["crop"] = {"start": float(m.group(1)), "end": float(m.group(2))}
        if "大声" in t:
            params["volume"] = {"gain": 2.0}
        elif "小声" in t:
            params["volume"] = {"gain": 0.5}
        if re.search(r"杂音|降噪|去噪|降噪点|清理背景音", t):
            params["denoise"] = True
        for fmt in ("mp3", "wav", "aac"):
            if f"转{fmt}" in t or fmt in t:
                params.setdefault("output_format", fmt)
        if "识别" in t or "转文字" in t:
            return {"action": "asr", "params": {}, "reply": "正在识别语音内容"}
        if params:
            return {"action": "audio_edit", "params": params, "reply": "已按你的要求处理音频"}
        return {"action": "reply", "params": {}, "reply": "请告诉我具体要做什么，例如：从5秒到20秒、大声一点、转mp3、识别语音内容。"}
    if re.search(
        r"生成|画一(张|幅|个)|画个|帮我画|帮我绘|绘制一(张|幅)|凭空|文生图|做一张|做一幅|创作一(张|幅)|"
        r"(生成|做|制作|设计|画|来|创建)(?![^，。]{0,6}(语音|音|文字))[^，。]{0,20}(图片|图|海报|封面|插画|头像|壁纸|背景|logo|照片|宣传图)",
        t,
        re.IGNORECASE,
    ):
        return {"action": "t2i", "params": {"prompt": t}, "reply": "正在生成图片，请稍候"}
    if re.search(r"转(成|为)?语音|朗读|语音合成|合成语音|文字转|tts", t, re.IGNORECASE):
        content = t
        for kw in ("语音合成", "转语音", "朗读", "合成", "tts"):
            content = content.replace(kw, "", 1)
        content = content.strip("：:，,。 ")
        return {"action": "tts", "params": {"text": content or text}, "reply": "正在合成语音"}
    return {"action": "reply", "params": {}, "reply": "我可以帮你剪辑图片和音频、识别语音、合成语音。可以发一张图片或一段音频，告诉我你的需求。"}


def _resolve_intent(text: str, media_kind: str, caption: str | None = None) -> dict:
    intent = parse_with_llm(text, media_kind, caption)
    if intent is not None:
        return intent
    return parse_with_rules(text, media_kind)


def _save_file(data: bytes, ext: str, task_dir: str) -> str:
    filename = f"media_{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(task_dir, filename), "wb") as f:
        f.write(data)
    return os.path.join(task_dir, filename)


def run_chat(params: dict, task_dir: str) -> dict:
    voice_path = params.get("voice_path")
    media_path = params.get("media_path")
    media_kind = params.get("media_kind")
    text = (params.get("text") or "").strip()

    voice_text = ""
    if voice_path and os.path.exists(voice_path):
        asr_result = ai_service.run_asr(voice_path, task_dir)
        voice_text = asr_result["text"]

    combined = f"{voice_text} {text}".strip()
    if not combined:
        return {"kind": "text", "text": "没有收到有效的文字或语音指令。", "filename": None}

    caption = None
    if media_kind == "image" and media_path and os.path.exists(media_path):
        caption = _image_caption(media_path)

    intent = _resolve_intent(combined, media_kind, caption)
    action = intent["action"]
    reply = intent.get("reply") or ""
    iparams = intent.get("params") or {}

    if action == "image_understand":
        if not media_path or not os.path.exists(media_path) or media_kind != "image":
            return {"kind": "text", "text": "需要上传图片才能识别内容。", "filename": None}
        if caption:
            return {"kind": "text", "text": f"我看到了：{caption}", "filename": None}
        return {"kind": "text", "text": "图片理解服务暂时不可用，请稍后再试或换一张图片。", "filename": None}

    if action == "reply":
        return {"kind": "text", "text": reply, "filename": None}

    if action == "t2i":
        prompt = (iparams.get("prompt") or "").strip() or combined
        try:
            filename = ai_service.run_t2i(prompt, task_dir)
        except Exception as exc:
            detail = str(getattr(exc, "detail", "") or exc)
            return {"kind": "text", "text": f"图片生成失败：{detail}", "filename": None}
        return {"kind": "image", "text": reply or "图片已生成", "filename": filename}

    if action == "i2i":
        if not media_path or not os.path.exists(media_path):
            return {"kind": "text", "text": "需要上传图片才能进行生成式修改。", "filename": None}
        if media_kind != "image":
            return {"kind": "text", "text": "生成式修改需要图片输入。", "filename": None}
        prompt = (iparams.get("prompt") or "").strip() or combined
        try:
            filename = ai_service.run_i2i(media_path, prompt, task_dir)
        except Exception as exc:
            detail = str(getattr(exc, "detail", "") or exc)
            return {"kind": "text", "text": f"图片修改失败：{detail}", "filename": None}
        return {"kind": "image", "text": reply or "已基于原图生成修改效果", "filename": filename}

    if action == "tts":
        tts_text = iparams.get("text") or text or combined
        filename = ai_service.run_tts(tts_text, task_dir)
        return {"kind": "audio", "text": reply or "已合成语音", "filename": filename}

    if action == "image_to_video":
        if not media_path or not os.path.exists(media_path):
            return {"kind": "text", "text": "需要上传图片才能生成视频。", "filename": None}
        if media_kind != "image":
            return {"kind": "text", "text": "视频生成需要图片输入。", "filename": None}
        duration = int(iparams.get("duration") or 5)
        motion = iparams.get("motion")
        if motion not in ("zoom", "pan"):
            motion = "pan" if re.search(r"驰骋|行驶|平移|横向|扫|公路|飞驰|移动|漂移", combined) else "zoom"
        filename = video_service.image_to_video(media_path, duration, task_dir, motion=motion)
        note = "（横向运镜）" if motion == "pan" else "（推进运镜）"
        return {
            "kind": "video",
            "text": f"已生成 {duration} 秒镜头运镜视频{note}。说明：这是镜头推拉/平移的运镜效果，画面中的车不会真的开动；真正的图生视频内容生成暂未接入。",
            "filename": filename,
        }

    if action == "asr":
        if not media_path or not os.path.exists(media_path):
            return {"kind": "text", "text": "需要上传音频文件才能识别语音。", "filename": None}
        result = ai_service.run_asr(media_path, task_dir)
        return {"kind": "text", "text": result["text"], "filename": result["filename"]}

    if action in ("matting", "enhance"):
        if not media_path or not os.path.exists(media_path):
            return {"kind": "text", "text": "需要上传图片才能处理。", "filename": None}
        if media_kind != "image":
            return {"kind": "text", "text": "抠图/增强需要图片输入。", "filename": None}
        filename = (
            ai_service.run_matting(media_path, task_dir)
            if action == "matting"
            else ai_service.run_enhance(media_path, task_dir)
        )
        return {"kind": "image", "text": reply or "处理完成", "filename": filename}

    if action == "image_edit":
        if not media_path or not os.path.exists(media_path):
            return {"kind": "text", "text": "需要上传图片才能编辑。", "filename": None}
        if media_kind != "image":
            return {"kind": "text", "text": "图片编辑需要图片输入。", "filename": None}
        with open(media_path, "rb") as f:
            data = f.read()
        result, output_format = image_service.process_image(data, iparams)
        filename = f"chat_{uuid.uuid4().hex}.{output_format}"
        with open(os.path.join(task_dir, filename), "wb") as f:
            f.write(result)
        return {"kind": "image", "text": reply or "图片处理完成", "filename": filename}

    if action == "audio_edit":
        if not media_path or not os.path.exists(media_path):
            return {"kind": "text", "text": "需要上传音频才能编辑。", "filename": None}
        if media_kind != "audio":
            return {"kind": "text", "text": "音频编辑需要音频输入。", "filename": None}
        with open(media_path, "rb") as f:
            data = f.read()
        ext = params.get("media_ext") or "wav"
        path, fmt = audio_service.process_audio(data, iparams, ext, task_dir)
        filename = os.path.basename(path)
        return {"kind": "audio", "text": reply or "音频处理完成", "filename": filename}

    return {"kind": "text", "text": "暂不支持该操作。", "filename": None}
