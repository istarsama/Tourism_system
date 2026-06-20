import json
import os

from passlib.context import CryptContext
from sqlmodel import Session, select

from database import engine, init_db
from models import Comment, Diary, NationalSpot, User
from poi_service import resolve_diary_poi_id

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _resolve_national_spot_id(session: Session, item: dict) -> int | None:
    if item.get("national_spot_id") is not None:
        return int(item["national_spot_id"])

    spot_name = item.get("national_spot_name")
    if not spot_name:
        return None

    stmt = select(NationalSpot).where(NationalSpot.name == spot_name, NationalSpot.is_active == True)
    if item.get("city"):
        stmt = stmt.where(NationalSpot.city == item["city"])
    spot = session.exec(stmt).first()
    return spot.id if spot else None


def import_mock_data():
    init_db()

    file_path = "src/mock_data.json"
    if not os.path.exists(file_path):
        print(f"找不到文件: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with Session(engine) as session:
        print("开始导入数据...")

        user_map = {}
        for username in data.get("users", []):
            existing_user = session.exec(select(User).where(User.username == username)).first()
            if not existing_user:
                existing_user = User(username=username, password_hash=pwd_context.hash("123456"))
                session.add(existing_user)
                session.commit()
                session.refresh(existing_user)
                print(f"   创建用户: {username}")
            user_map[username] = existing_user.id

        for item in data.get("diaries", []):
            author_id = user_map.get(item["username"])
            if not author_id:
                print(f"   跳过日记，找不到用户: {item['username']}")
                continue

            scope = item.get("scope", "campus")
            spot_id = item.get("spot_id") if scope == "campus" else None
            national_spot_id = _resolve_national_spot_id(session, item) if scope == "national" else None

            if scope == "national" and national_spot_id is None:
                print(f"   跳过全国日记，找不到景点: {item.get('title')}")
                continue

            existing = session.exec(
                select(Diary).where(Diary.user_id == author_id, Diary.title == item["title"])
            ).first()

            poi_id = resolve_diary_poi_id(
                session,
                scope=scope,
                spot_id=spot_id,
                national_spot_id=national_spot_id,
            )

            if existing:
                diary = existing
                diary.poi_id = poi_id
                diary.spot_id = spot_id
                diary.scope = scope
                diary.national_spot_id = national_spot_id
                diary.content = item["content"]
                diary.score = item.get("score", diary.score)
                diary.view_count = item.get("view_count", diary.view_count)
                diary.media_json = json.dumps(item.get("media_files", []), ensure_ascii=False)
                print(f"   更新日记: {diary.title} (ID: {diary.id})")
            else:
                diary = Diary(
                    user_id=author_id,
                    poi_id=poi_id,
                    spot_id=spot_id,
                    scope=scope,
                    national_spot_id=national_spot_id,
                    title=item["title"],
                    content=item["content"],
                    score=item.get("score", 5.0),
                    view_count=item.get("view_count", 0),
                    media_json=json.dumps(item.get("media_files", []), ensure_ascii=False),
                )
                session.add(diary)
                session.commit()
                session.refresh(diary)
                print(f"   发布日记: {diary.title} (ID: {diary.id})")

            session.add(diary)
            session.commit()
            session.refresh(diary)

            for c in item.get("comments", []):
                commenter_id = user_map.get(c["username"])
                if not commenter_id:
                    continue
                exists_comment = session.exec(
                    select(Comment).where(
                        Comment.user_id == commenter_id,
                        Comment.diary_id == diary.id,
                        Comment.content == c["content"],
                    )
                ).first()
                if exists_comment:
                    continue
                session.add(
                    Comment(
                        user_id=commenter_id,
                        diary_id=diary.id,
                        content=c["content"],
                        score=c.get("score", 5.0),
                    )
                )
            session.commit()

    print("所有数据导入完成！")


if __name__ == "__main__":
    import_mock_data()
