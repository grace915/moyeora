"""
Moyeora — 링크 하나로 약속 잡기
================================
실행: python app.py    →  http://localhost:5001
"""
from __future__ import annotations

import calendar
import os
import secrets
from datetime import date, timedelta
from flask import (
    Flask, flash, redirect, render_template, request, url_for,
)

import db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "moyeora-dev-secret-change-me"
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

db.init_db()

WEEKDAYS_KOR = ["일", "월", "화", "수", "목", "금", "토"]

# 캘린더 표시 범위 (오늘부터 N일)
CALENDAR_DAYS = 365

# 월별 테마: 라벨 + 대표 이모지(스티커) + 영문 표기
MONTH_THEMES = {
    1:  {"name": "JANUARY",   "ko": "1월",  "tagline": "FRESH NEW YEAR",        "stickers": ["🍓", "❄️", "✨", "⭐"]},
    2:  {"name": "FEBRUARY",  "ko": "2월",  "tagline": "SWEET LITTLE THINGS",   "stickers": ["💝", "🌸", "🍫", "✨"]},
    3:  {"name": "MARCH",     "ko": "3월",  "tagline": "HELLO, BLOSSOMS!",      "stickers": ["🌸", "🌱", "🦋", "✿"]},
    4:  {"name": "APRIL",     "ko": "4월",  "tagline": "NATURE'S CANDY",        "stickers": ["🍊", "🌼", "🌿", "✨"]},
    5:  {"name": "MAY",       "ko": "5월",  "tagline": "ROSES & PICNICS",       "stickers": ["🌹", "🍃", "🧺", "☀️"]},
    6:  {"name": "JUNE",      "ko": "6월",  "tagline": "JUICY DAYS",            "stickers": ["🫐", "💧", "🌿", "✨"]},
    7:  {"name": "JULY",      "ko": "7월",  "tagline": "SUMMER VIBES ONLY",     "stickers": ["🍉", "🌊", "🍦", "☀️"]},
    8:  {"name": "AUGUST",    "ko": "8월",  "tagline": "HOT & SUNNY",           "stickers": ["🌻", "🍑", "☀️", "✨"]},
    9:  {"name": "SEPTEMBER", "ko": "9월",  "tagline": "GRAPE SEASON",          "stickers": ["🍇", "🍂", "📚", "✨"]},
    10: {"name": "OCTOBER",   "ko": "10월", "tagline": "SPOOKY & COZY",         "stickers": ["🎃", "🍁", "👻", "🕸️"]},
    11: {"name": "NOVEMBER",  "ko": "11월", "tagline": "WARM PERSIMMON DAYS",   "stickers": ["🍊", "🍂", "🧣", "✨"]},
    12: {"name": "DECEMBER",  "ko": "12월", "tagline": "MERRY EVERYTHING",      "stickers": ["🎄", "❄️", "🎁", "⭐"]},
}


# ── 템플릿 헬퍼 ────────────────────────────────────────────────
@app.template_filter("fmt_date")
def fmt_date(iso_str: str) -> str:
    if not iso_str:
        return ""
    try:
        d = date.fromisoformat(iso_str)
    except ValueError:
        return iso_str
    return f"{d.strftime('%Y-%m-%d')} ({WEEKDAYS_KOR[d.weekday()]})"


def build_calendar_months(range_start: date, range_end: date) -> list[dict]:
    months = []
    cursor = date(range_start.year, range_start.month, 1)
    while cursor <= range_end:
        cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
        weeks_raw = cal.monthdatescalendar(cursor.year, cursor.month)
        weeks = []
        for week in weeks_raw:
            row = []
            for d in week:
                if d.month != cursor.month:
                    row.append(None)
                else:
                    row.append({
                        "day": d.day,
                        "iso": d.isoformat(),
                        "in_range": range_start <= d <= range_end,
                        "weekday": d.weekday(),
                    })
            weeks.append(row)
        theme = MONTH_THEMES[cursor.month]
        months.append({
            "year": cursor.year,
            "month": cursor.month,
            "weeks": weeks,
            "theme": theme,
        })
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return months


# ── 라우트 ─────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/new", methods=["POST"])
def new_appointment():
    """새 약속 링크를 즉석에서 생성."""
    slug = secrets.token_urlsafe(6)
    return redirect(url_for("view_event", slug=slug))


@app.route("/e/<slug>")
def view_event(slug: str):
    current_name = (request.args.get("name") or "").strip()

    today = date.today()
    range_start = today
    range_end = today + timedelta(days=CALENDAR_DAYS)
    months = build_calendar_months(range_start, range_end)

    responses = db.get_responses(slug)
    participants = sorted(responses.keys())
    total_people = len(participants)
    my_dates = responses.get(current_name, set()) if current_name else set()

    date_counts: dict[str, list[str]] = {}
    for name, dates in responses.items():
        for d in dates:
            date_counts.setdefault(d, []).append(name)
    for d in date_counts:
        date_counts[d].sort()

    everyone_dates = sorted(
        d for d, names in date_counts.items() if len(names) == total_people
    ) if total_people > 0 else []

    finalized_date = db.get_finalized(slug)

    return render_template(
        "event.html",
        slug=slug,
        months=months,
        weekday_labels=WEEKDAYS_KOR,
        participants=participants,
        total_people=total_people,
        date_counts=date_counts,
        everyone_dates=everyone_dates,
        current_name=current_name,
        my_availability=sorted(my_dates),
        finalized_date=finalized_date,
    )


@app.route("/e/<slug>/save", methods=["POST"])
def save_response(slug: str):
    name = (request.form.get("name") or "").strip()
    dates = request.form.getlist("dates")

    if not name:
        flash("이름을 입력해주세요.", "error")
        return redirect(url_for("view_event", slug=slug))

    if db.get_finalized(slug):
        flash("이미 확정된 약속은 수정할 수 없어요.", "error")
        return redirect(url_for("view_event", slug=slug))

    db.save_response(slug, name, dates)
    flash(f"{name}님의 가능일이 저장되었습니다. ({len(dates)}일)", "success")
    return redirect(url_for("view_event", slug=slug, name=name))


@app.route("/e/<slug>/finalize", methods=["POST"])
def finalize(slug: str):
    final_date = (request.form.get("final_date") or "").strip()
    if not final_date:
        flash("확정할 날짜를 선택해주세요.", "error")
        return redirect(url_for("view_event", slug=slug))

    # 정말 모두 가능한 날인지 검증
    responses = db.get_responses(slug)
    if not responses:
        flash("아직 응답이 없어요.", "error")
        return redirect(url_for("view_event", slug=slug))
    total = len(responses)
    available = sum(1 for ds in responses.values() if final_date in ds)
    if available != total:
        flash("모두가 가능한 날짜만 확정할 수 있어요.", "error")
        return redirect(url_for("view_event", slug=slug))

    try:
        db.set_finalized(slug, final_date)
    except ValueError:
        flash("올바른 날짜 형식이 아니에요.", "error")
        return redirect(url_for("view_event", slug=slug))

    flash(f"🎉 {final_date} 로 확정되었어요!", "success")
    return redirect(url_for("view_event", slug=slug))


@app.route("/e/<slug>/unfinalize", methods=["POST"])
def unfinalize(slug: str):
    db.clear_finalized(slug)
    flash("확정이 취소되었어요.", "success")
    return redirect(url_for("view_event", slug=slug))


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, port=5001)
