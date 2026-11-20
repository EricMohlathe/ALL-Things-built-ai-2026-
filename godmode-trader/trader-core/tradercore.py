#!/usr/bin/env python3
"""tradercore: the shared engine of the GODMODE Multi-Asset Trader. Standard library only.

Every tool in the pack imports this one file, so they all agree on:

  Instruments  about 110 built in: forex majors, crosses and exotics; metals,
               energy and grains (CFD style and CME futures); cash indices and
               index futures; crypto. Each one carries its Yahoo feed, tick,
               pip, contract size, lot step, quote currency, default session,
               a typical spread and the ESMA retail leverage cap. Override any
               field, or add your own instrument, in trader/config.json
               ("instruments") or trader/instruments.json.
  Sessions     London, New York, Tokyo, Sydney, the Asian range, US cash,
               COMEX, NYMEX, CBOT, Xetra, LSE, Euronext, TSE, HKEX, ASX and the
               crypto UTC day. A session is a window in its own time zone, so
               "London 08:00" stays 08:00 London across both DST changes.
  Time zones   built-in DST rules for the US, the EU, Sydney and Auckland plus
               the fixed-offset zones, so no tz database is needed. Any other
               IANA name works where Python has zoneinfo.
  Data         Yahoo Finance v8 chart bars (free, unofficial, can lag) with
               host fallback and a 429 back-off, or saved files (--offline).
  Money        Decimal rounding to the instrument's tick, pips and points,
               quote-to-account currency conversion, lots and units.

Run it to see the registry:

    python3 tradercore.py instruments [--class forex]
    python3 tradercore.py sessions
    python3 tradercore.py show XAUUSD
    python3 tradercore.py clock [--now "2026-11-16 08:45 London"]
"""

import argparse
import datetime
import difflib
import gzip
import importlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP

VERSION = "3.0.0"
UA = "Mozilla/5.0 (compatible; godmode-trader/%s)" % VERSION
YAHOO_HOSTS = ("query2", "query1")
PAUSE = 0.3          # seconds between requests: be polite to free endpoints
BACKOFF = 5.0        # seconds before the one retry after an HTTP 429
SETTLE = 60          # seconds a closed bar may wait for Yahoo to catch up
SLEEP = time.sleep   # tests swap this out
OPENER = None        # tests swap this for a fake network: OPENER(url, timeout, headers) -> text
EPOCH = datetime.datetime(1970, 1, 1)
CLASSES = ("forex", "commodity", "index", "crypto")
INTERVALS = {"1m": 60, "5m": 300, "15m": 900}
NOTE_ADVICE = "Education and tooling, not financial advice."


class TraderError(Exception):
    pass


# ================================================================ time

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


def utc_of(ts):
    """Unix seconds -> naive UTC. Never uses the machine's time zone."""
    return EPOCH + datetime.timedelta(seconds=int(ts))


def ts_of(utc):
    return int((utc.replace(tzinfo=None) - EPOCH).total_seconds())


def iso(utc):
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(text):
    """'2026-11-16T08:45:00Z' (or any ISO time with an offset) -> naive UTC, or None."""
    if not text:
        return None
    try:
        dt = datetime.datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = (dt - dt.utcoffset()).replace(tzinfo=None)
    return dt


# minutes from UTC in standard time, and the DST rule (None = no DST)
ZONES = {
    "UTC": (0, None),
    "America/New_York": (-300, "us"),
    "America/Chicago": (-360, "us"),
    "America/Toronto": (-300, "us"),
    "Europe/London": (0, "eu"),
    "Europe/Dublin": (0, "eu"),
    "Europe/Berlin": (60, "eu"),
    "Europe/Paris": (60, "eu"),
    "Europe/Zurich": (60, "eu"),
    "Europe/Amsterdam": (60, "eu"),
    "Europe/Madrid": (60, "eu"),
    "Europe/Prague": (60, "eu"),
    "Europe/Athens": (120, "eu"),
    "Europe/Helsinki": (120, "eu"),
    "Asia/Jerusalem": (120, "il"),
    "FX/NewYork_Close": (120, "usfx"),       # most MT5 servers: midnight = 17:00 New York, UTC+2 / +3
    "Africa/Johannesburg": (120, None),
    "Africa/Lagos": (60, None),
    "Africa/Nairobi": (180, None),
    "Asia/Dubai": (240, None),
    "Asia/Kolkata": (330, None),
    "Asia/Singapore": (480, None),
    "Asia/Hong_Kong": (480, None),
    "Asia/Shanghai": (480, None),
    "Asia/Tokyo": (540, None),
    "Australia/Sydney": (600, "au"),
    "Pacific/Auckland": (720, "nz"),
}
ZONE_ALIASES = {
    "Z": "UTC", "GMT": "UTC", "UTC": "UTC",
    "ET": "America/New_York", "EST": "America/New_York", "EDT": "America/New_York",
    "NY": "America/New_York", "NEWYORK": "America/New_York", "NEW_YORK": "America/New_York",
    "CT": "America/Chicago", "CST": "America/Chicago", "CDT": "America/Chicago", "CHICAGO": "America/Chicago",
    "LONDON": "Europe/London", "UK": "Europe/London", "BST": "Europe/London",
    "CET": "Europe/Berlin", "CEST": "Europe/Berlin", "FRANKFURT": "Europe/Berlin", "BERLIN": "Europe/Berlin",
    "PARIS": "Europe/Paris", "ZURICH": "Europe/Zurich",
    "SAST": "Africa/Johannesburg", "JOHANNESBURG": "Africa/Johannesburg", "JHB": "Africa/Johannesburg",
    "DUBAI": "Asia/Dubai", "IST": "Asia/Kolkata", "SGT": "Asia/Singapore", "SINGAPORE": "Asia/Singapore",
    "HKT": "Asia/Hong_Kong", "HONGKONG": "Asia/Hong_Kong", "HONG_KONG": "Asia/Hong_Kong",
    "JST": "Asia/Tokyo", "TOKYO": "Asia/Tokyo",
    "AEST": "Australia/Sydney", "AEDT": "Australia/Sydney", "SYDNEY": "Australia/Sydney",
    "NZST": "Pacific/Auckland", "NZDT": "Pacific/Auckland", "AUCKLAND": "Pacific/Auckland",
    "PRAGUE": "Europe/Prague", "FTMO": "Europe/Prague", "ATHENS": "Europe/Athens", "EET": "Europe/Athens",
    "EEST": "Europe/Athens", "MT5": "FX/NewYork_Close", "MT5_SERVER": "FX/NewYork_Close",
    "NY_CLOSE": "FX/NewYork_Close", "SERVER": "FX/NewYork_Close",
}
ZONE_LABEL = {
    "UTC": "UTC", "America/New_York": "New York", "America/Chicago": "Chicago", "Europe/London": "London",
    "Europe/Berlin": "Frankfurt", "Europe/Paris": "Paris", "Europe/Zurich": "Zurich",
    "Africa/Johannesburg": "Johannesburg", "Asia/Tokyo": "Tokyo", "Asia/Hong_Kong": "Hong Kong",
    "Asia/Singapore": "Singapore", "Australia/Sydney": "Sydney", "Pacific/Auckland": "Auckland",
    "Asia/Dubai": "Dubai", "Asia/Kolkata": "Mumbai", "Asia/Shanghai": "Shanghai", "Europe/Prague": "Prague",
    "Europe/Athens": "Athens", "FX/NewYork_Close": "MT5 server (New York close)",
}


def _zoneinfo(name):
    """zoneinfo.ZoneInfo(name) where Python has it (3.9+ with tz data), else None."""
    try:
        zi = importlib.import_module("zoneinfo")
        return zi.ZoneInfo(name)
    except Exception:
        return None


def zone_name(name, strict=True):
    """'London', 'ET', 'Europe/London' -> 'Europe/London'. None (or an error) when unknown."""
    if not name:
        return "UTC"
    raw = str(name).strip()
    if raw in ZONES:
        return raw
    key = raw.upper().replace(" ", "_")
    if key in ZONE_ALIASES:
        return ZONE_ALIASES[key]
    for z in ZONES:
        if z.upper() == key:
            return z
    if "/" in raw and _zoneinfo(raw) is not None:
        return raw
    if strict:
        raise TraderError("unknown time zone %r: use an IANA name like Europe/London or one of %s"
                          % (name, ", ".join(sorted(set(ZONE_ALIASES) - {"Z"}))[:200]))
    return None


def zone_label(zone):
    z = zone_name(zone)
    return ZONE_LABEL.get(z, z)


def _nth_weekday(year, month, weekday, n):
    """The n-th weekday (0 = Monday) of a month; n = -1 is the last one."""
    if n > 0:
        d = datetime.date(year, month, 1)
        d += datetime.timedelta(days=(weekday - d.weekday()) % 7)
        return d + datetime.timedelta(weeks=n - 1)
    nxt = datetime.date(year + (month == 12), month % 12 + 1, 1)
    d = nxt - datetime.timedelta(days=1)
    return d - datetime.timedelta(days=(d.weekday() - weekday) % 7)


def _dst_window(rule, year, std):
    """(start, end) of daylight time in naive UTC for one calendar year."""
    def at(day, hh, minutes_from_utc):
        return datetime.datetime.combine(day, datetime.time(hh)) - datetime.timedelta(minutes=minutes_from_utc)
    if rule == "us":   # 2:00 local, 2nd Sunday of March to 1st Sunday of November (since 2007)
        return at(_nth_weekday(year, 3, 6, 2), 2, std), at(_nth_weekday(year, 11, 6, 1), 2, std + 60)
    if rule == "eu":   # 01:00 UTC, last Sunday of March to last Sunday of October
        return at(_nth_weekday(year, 3, 6, -1), 1, 0), at(_nth_weekday(year, 10, 6, -1), 1, 0)
    if rule == "au":   # 2:00 standard, 1st Sunday of October; ends 3:00 daylight, 1st Sunday of April
        return at(_nth_weekday(year, 10, 6, 1), 2, std), at(_nth_weekday(year, 4, 6, 1), 3, std + 60)
    if rule == "nz":   # 2:00 standard, last Sunday of September; ends 3:00 daylight, 1st Sunday of April
        return at(_nth_weekday(year, 9, 6, -1), 2, std), at(_nth_weekday(year, 4, 6, 1), 3, std + 60)
    if rule == "usfx":  # switches with New York: 2:00 NY on the US dates, whatever the zone's own offset
        return at(_nth_weekday(year, 3, 6, 2), 2, -300), at(_nth_weekday(year, 11, 6, 1), 2, -240)
    if rule == "il":   # Israel: Friday before the last Sunday of March 2:00, last Sunday of October 2:00
        return (at(_nth_weekday(year, 3, 6, -1) - datetime.timedelta(days=2), 2, std),
                at(_nth_weekday(year, 10, 6, -1), 2, std + 60))
    raise TraderError("unknown DST rule %r" % rule)


def offset_minutes(zone, utc):
    """Minutes from UTC for `zone` at the naive-UTC moment `utc`."""
    z = zone_name(zone)
    utc = utc.replace(tzinfo=None)
    if z in ZONES:
        std, rule = ZONES[z]
        if not rule:
            return std
        start, end = _dst_window(rule, utc.year, std)
        if start < end:                  # northern hemisphere
            dst = start <= utc < end
        else:                            # southern: daylight from October to April
            dst = utc >= start or utc < end
        return std + 60 if dst else std
    zi = _zoneinfo(z)
    if zi is None:
        raise TraderError("time zone %s needs Python 3.9+ with tz data; use one of the built-in zones" % z)
    aware = utc.replace(tzinfo=datetime.timezone.utc).astimezone(zi)
    return int(aware.utcoffset().total_seconds() // 60)


def to_local(zone, utc):
    return utc.replace(tzinfo=None) + datetime.timedelta(minutes=offset_minutes(zone, utc))


def to_utc(zone, local):
    """Naive local wall-clock time in `zone` -> naive UTC. In the autumn hour that
    happens twice it picks the first (daylight) one; a spring-gap time moves forward."""
    local = local.replace(tzinfo=None)
    day = datetime.timedelta(days=1)
    cands = sorted({offset_minutes(zone, local - day), offset_minutes(zone, local),
                    offset_minutes(zone, local + day)}, reverse=True)
    for off in cands:
        u = local - datetime.timedelta(minutes=off)
        if offset_minutes(zone, u) == off:
            return u
    return local - datetime.timedelta(minutes=min(cands))


def stamp(utc, zone, seconds=False):
    """'Mon 2026-11-16 08:45 London'."""
    loc = to_local(zone, utc)
    return "%s %s" % (loc.strftime("%a %Y-%m-%d %H:%M" + (":%S" if seconds else "")), zone_label(zone))


def hm(t):
    return "%02d:%02d" % (t.hour, t.minute)


def ampm(t):
    h = t.hour % 12 or 12
    return "%d:%02d %s" % (h, t.minute, "AM" if t.hour < 12 else "PM")


def parse_hhmm(text, what="a time"):
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", str(text or ""))
    if not m or int(m.group(1)) > 24 or int(m.group(2)) > 59 or (int(m.group(1)) == 24 and int(m.group(2))):
        raise TraderError("%s wants a clock time like 08:45, not %r" % (what, text))
    return int(m.group(1)) * 60 + int(m.group(2))


def parse_now(text, zone="UTC"):
    """--now -> naive UTC. Forms:
         "2026-11-16 08:45"           wall-clock time in `zone` (the session's or the config's)
         "2026-11-16 08:45 London"    a zone word at the end wins
         "08:45" / "08:45 NY"         today in that zone
         "2026-11-16T08:45:00Z"       absolute (Z or an offset)"""
    if not text:
        return utc_now()
    t = str(text).strip()
    m = re.match(r"^(.*\d)\s*([A-Za-z][A-Za-z_/]*)$", t)
    if m and not re.search(r"[+-]\d{2}:?\d{2}$", t):
        z = zone_name(m.group(2), strict=False)
        if z:
            t, zone = m.group(1).strip(), z
    if re.match(r"^\d{1,2}:\d{2}$", t):
        t = "%s %s" % (to_local(zone, utc_now()).date().isoformat(), t.zfill(5))
    try:
        dt = datetime.datetime.fromisoformat(t.replace("Z", "+00:00") if t.endswith("Z") else t)
    except ValueError:
        raise TraderError('--now wants a time like "2026-11-16 08:45", "2026-11-16 08:45 London" or '
                          '"2026-11-16T08:45:00Z", not %r' % text)
    if dt.tzinfo is not None:
        return (dt - dt.utcoffset()).replace(tzinfo=None)
    return to_utc(zone, dt)


# ================================================================ holidays

NYSE_HOLIDAYS = {  # https://www.nyse.com/markets/hours-calendars (2026 and 2027)
    "2026-01-01": "New Year's Day", "2026-01-19": "Martin Luther King, Jr. Day",
    "2026-02-16": "Washington's Birthday", "2026-04-03": "Good Friday", "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth", "2026-07-03": "Independence Day (observed)", "2026-09-07": "Labor Day",
    "2026-11-26": "Thanksgiving Day", "2026-12-25": "Christmas Day",
    "2027-01-01": "New Year's Day", "2027-01-18": "Martin Luther King, Jr. Day",
    "2027-02-15": "Washington's Birthday", "2027-03-26": "Good Friday", "2027-05-31": "Memorial Day",
    "2027-06-18": "Juneteenth (observed)", "2027-07-05": "Independence Day (observed)",
    "2027-09-06": "Labor Day", "2027-11-25": "Thanksgiving Day", "2027-12-24": "Christmas Day (observed)",
}
NYSE_EARLY_CLOSE = {  # 1:00 p.m. New York
    "2026-11-27": "day after Thanksgiving", "2026-12-24": "Christmas Eve", "2027-11-26": "day after Thanksgiving",
}
NYSE_YEARS = (2026, 2027)


def easter(year):
    """Gregorian Easter Sunday (the anonymous algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return datetime.date(year, month, day)


def _weekday_sub(d):
    """A UK bank holiday on a weekend moves to the next weekday."""
    while d.weekday() >= 5:
        d += datetime.timedelta(days=1)
    return d


def _rule_holidays(cal, year):
    """{iso: name} for the calendars that follow fixed rules (FX, LSE, Xetra, Euronext)."""
    e = easter(year)
    gf, em = e - datetime.timedelta(days=2), e + datetime.timedelta(days=1)
    out = {}
    if cal == "fx":
        out["%d-01-01" % year] = "New Year's Day (FX closed)"
        out["%d-12-25" % year] = "Christmas Day (FX closed)"
    elif cal == "lse":
        out[_weekday_sub(datetime.date(year, 1, 1)).isoformat()] = "New Year's Day"
        out[gf.isoformat()] = "Good Friday"
        out[em.isoformat()] = "Easter Monday"
        out[_nth_weekday(year, 5, 0, 1).isoformat()] = "Early May bank holiday"
        out[_nth_weekday(year, 5, 0, -1).isoformat()] = "Spring bank holiday"
        out[_nth_weekday(year, 8, 0, -1).isoformat()] = "Summer bank holiday"
        xmas = _weekday_sub(datetime.date(year, 12, 25))
        out[xmas.isoformat()] = "Christmas Day"
        boxing = _weekday_sub(max(xmas + datetime.timedelta(days=1), datetime.date(year, 12, 26)))
        out[boxing.isoformat()] = "Boxing Day"
    elif cal == "xetra":
        for md, name in (("01-01", "New Year's Day"), ("05-01", "Labour Day"), ("12-24", "Christmas Eve"),
                         ("12-25", "Christmas Day"), ("12-26", "Boxing Day"), ("12-31", "New Year's Eve")):
            out["%d-%s" % (year, md)] = name
        out[gf.isoformat()] = "Good Friday"
        out[em.isoformat()] = "Easter Monday"
    elif cal == "euronext":
        for md, name in (("01-01", "New Year's Day"), ("05-01", "Labour Day"), ("12-25", "Christmas Day"),
                         ("12-26", "Boxing Day")):
            out["%d-%s" % (year, md)] = name
        out[gf.isoformat()] = "Good Friday"
        out[em.isoformat()] = "Easter Monday"
    return out


CALENDAR_LABEL = {"nyse": "NYSE", "cme": "CME (US holidays)", "fx": "FX market", "lse": "LSE", "xetra": "Xetra",
                  "euronext": "Euronext", "jpx": "JPX", "hkex": "HKEX", "asx": "ASX", "none": "24/7"}


def holiday(cal, day):
    """The holiday's name if `cal` is closed all day on `day`, else None."""
    k = day.isoformat()
    if cal in ("nyse", "cme"):
        return NYSE_HOLIDAYS.get(k)
    if cal in ("fx", "lse", "xetra", "euronext"):
        return _rule_holidays(cal, day.year).get(k)
    return None


def early_close(cal, day):
    """(close 'HH:MM', why) for a shortened session, else None."""
    k = day.isoformat()
    if cal == "nyse" and k in NYSE_EARLY_CLOSE:
        return "13:00", NYSE_EARLY_CLOSE[k]
    if cal == "lse" and day.month == 12 and day.day in (24, 31) and day.weekday() < 5:
        return "12:30", "LSE half day"
    if cal == "euronext" and day.month == 12 and day.day in (24, 31) and day.weekday() < 5:
        return "14:05", "Euronext half day"
    return None


def calendar_known(cal, year):
    """True when the holiday list of `cal` is modeled for `year`."""
    if cal in ("nyse", "cme"):
        return year in NYSE_YEARS
    return cal in ("fx", "lse", "xetra", "euronext", "none")


# ================================================================ sessions

WEEKDAYS = (0, 1, 2, 3, 4)
EVERY_DAY = (0, 1, 2, 3, 4, 5, 6)
SESSIONS = {
    # forex sessions (OTC, 24 hours a day Sunday 17:00 to Friday 17:00 New York)
    "london": {"tz": "Europe/London", "open": "08:00", "close": "17:00", "days": WEEKDAYS, "calendar": "fx",
               "range": 30, "label": "London session"},
    "ny": {"tz": "America/New_York", "open": "08:00", "close": "17:00", "days": WEEKDAYS, "calendar": "fx",
           "range": 30, "label": "New York session"},
    "tokyo": {"tz": "Asia/Tokyo", "open": "09:00", "close": "18:00", "days": WEEKDAYS, "calendar": "fx",
              "range": 30, "label": "Tokyo session"},
    "sydney": {"tz": "Australia/Sydney", "open": "07:00", "close": "16:00", "days": WEEKDAYS, "calendar": "fx",
               "range": 30, "label": "Sydney session"},
    "asia_london": {"tz": "Europe/London", "open": "00:00", "close": "17:00", "days": WEEKDAYS, "calendar": "fx",
                    "range": 420, "label": "Asian range, London breakout"},
    # exchange sessions
    "us_cash": {"tz": "America/New_York", "open": "09:30", "close": "16:00", "days": WEEKDAYS, "calendar": "nyse",
                "range": 15, "label": "US cash session (NYSE hours)"},
    "comex": {"tz": "America/New_York", "open": "08:20", "close": "13:30", "days": WEEKDAYS, "calendar": "cme",
              "range": 15, "label": "COMEX metals day session"},
    "comex_copper": {"tz": "America/New_York", "open": "08:10", "close": "13:00", "days": WEEKDAYS,
                     "calendar": "cme", "range": 15, "label": "COMEX copper day session"},
    "nymex": {"tz": "America/New_York", "open": "09:00", "close": "14:30", "days": WEEKDAYS, "calendar": "cme",
              "range": 15, "label": "NYMEX energy day session"},
    "cbot": {"tz": "America/Chicago", "open": "08:30", "close": "13:20", "days": WEEKDAYS, "calendar": "cme",
             "range": 15, "label": "CBOT grains day session"},
    "xetra": {"tz": "Europe/Berlin", "open": "09:00", "close": "17:30", "days": WEEKDAYS, "calendar": "xetra",
              "range": 15, "label": "Xetra / Eurex cash session"},
    "lse": {"tz": "Europe/London", "open": "08:00", "close": "16:30", "days": WEEKDAYS, "calendar": "lse",
            "range": 15, "label": "London Stock Exchange session"},
    "euronext": {"tz": "Europe/Paris", "open": "09:00", "close": "17:30", "days": WEEKDAYS, "calendar": "euronext",
                 "range": 15, "label": "Euronext Paris session"},
    "tse": {"tz": "Asia/Tokyo", "open": "09:00", "close": "15:30", "days": WEEKDAYS, "calendar": "jpx",
            "breaks": [("11:30", "12:30")], "range": 15, "label": "Tokyo Stock Exchange session"},
    "hkex": {"tz": "Asia/Hong_Kong", "open": "09:30", "close": "16:00", "days": WEEKDAYS, "calendar": "hkex",
             "breaks": [("12:00", "13:00")], "range": 15, "label": "Hong Kong Exchange session"},
    "asx": {"tz": "Australia/Sydney", "open": "10:00", "close": "16:00", "days": WEEKDAYS, "calendar": "asx",
            "range": 15, "label": "ASX session"},
    # crypto (24/7)
    "utc": {"tz": "UTC", "open": "00:00", "close": "24:00", "days": EVERY_DAY, "calendar": "none",
            "range": 60, "label": "crypto UTC day"},
    "crypto_ny": {"tz": "America/New_York", "open": "09:30", "close": "16:00", "days": EVERY_DAY,
                  "calendar": "none", "range": 15, "label": "crypto during US hours"},
}
FX_SESSIONS = ("sydney", "tokyo", "london", "ny")


def session_def(name, cfg=None):
    """The session template, with trader/config.json "sessions" overrides applied."""
    if name not in SESSIONS:
        raise TraderError("unknown session %r: one of %s" % (name, ", ".join(sorted(SESSIONS))))
    s = dict(SESSIONS[name], name=name)
    over = ((cfg or {}).get("sessions") or {}).get(name) or {}
    for k in ("open", "close", "range", "no_entries_before", "no_entries_after", "flat_by", "label"):
        if over.get(k) is not None:
            s[k] = over[k]
    s["tz"] = zone_name(s["tz"])
    for k in ("open", "close"):
        parse_hhmm(s[k], "session %s %s" % (name, k))
    return s


def closed_reason(name, day, cfg=None):
    """Why `name` has no session on `day` (a date in the session's zone), or '' if it trades."""
    s = session_def(name, cfg)
    if day.weekday() not in s["days"]:
        return "weekend"
    hol = holiday(s["calendar"], day)
    if hol:
        return "%s holiday: %s" % (CALENDAR_LABEL.get(s["calendar"], s["calendar"]), hol)
    return ""


def session_instance(name, day, cfg=None):
    """One trading session on the local date `day`, or None when closed that day.
    Times are naive UTC (open_utc, close_utc, breaks_utc) and naive local."""
    s = session_def(name, cfg)
    if closed_reason(name, day, cfg):
        return None
    base = datetime.datetime.combine(day, datetime.time())
    o = parse_hhmm(s["open"])
    early = early_close(s["calendar"], day)
    c = parse_hhmm(early[0] if early else s["close"])
    open_local = base + datetime.timedelta(minutes=o)
    close_local = base + datetime.timedelta(minutes=c)
    if c <= o:
        close_local += datetime.timedelta(days=1)
    tz = s["tz"]
    breaks = []
    for bs, be in s.get("breaks") or []:
        b0, b1 = base + datetime.timedelta(minutes=parse_hhmm(bs)), base + datetime.timedelta(minutes=parse_hhmm(be))
        if open_local < b0 < close_local:
            breaks.append((to_utc(tz, b0), to_utc(tz, min(b1, close_local))))
    return {"session": name, "label": s["label"], "date": day.isoformat(), "tz": tz,
            "open_local": open_local, "close_local": close_local,
            "normal_close_local": base + datetime.timedelta(minutes=parse_hhmm(s["close"])) +
            (datetime.timedelta(days=1) if parse_hhmm(s["close"]) <= o else datetime.timedelta()),
            "open_utc": to_utc(tz, open_local), "close_utc": to_utc(tz, close_local), "breaks_utc": breaks,
            "early": early[1] if early else None, "range": int(s["range"]), "calendar": s["calendar"],
            "calendar_known": calendar_known(s["calendar"], day.year), "def": s}


def locate(name, now_utc, cfg=None):
    """(session instance, phase) for the clock: phase is 'open', 'pre-open' or 'closed'
    (today's session is over). (None, reason) when the session does not trade today."""
    s = session_def(name, cfg)
    today = to_local(s["tz"], now_utc).date()
    for d in (today - datetime.timedelta(days=1), today):
        inst = session_instance(name, d, cfg)
        if inst and inst["open_utc"] <= now_utc < inst["close_utc"]:
            return inst, "open"
    inst = session_instance(name, today, cfg)
    if inst:
        return inst, ("pre-open" if now_utc < inst["open_utc"] else "closed")
    return None, closed_reason(name, today, cfg)


def instance_on(name, date_text, cfg=None):
    """The session on an explicit YYYY-MM-DD, with a plain error when it did not trade."""
    try:
        day = datetime.date.fromisoformat(str(date_text))
    except ValueError:
        raise TraderError("a date like 2026-11-16, not %r" % date_text)
    inst = session_instance(name, day, cfg)
    if not inst:
        raise TraderError("no %s on %s (%s)" % (SESSIONS[name]["label"], day_label(day),
                                               closed_reason(name, day, cfg)))
    return inst


def next_open(name, now_utc, cfg=None):
    """The next session instance that opens after now_utc."""
    s = session_def(name, cfg)
    today = to_local(s["tz"], now_utc).date()
    for k in range(0, 15):
        inst = session_instance(name, today + datetime.timedelta(days=k), cfg)
        if inst and inst["open_utc"] > now_utc:
            return inst
    return None


def slots(inst, step):
    """Bar start times (naive UTC) of a session instance at `step` seconds, breaks left out."""
    if ts_of(inst["open_utc"]) % step:
        raise TraderError("the %s opens at %s, which is not on the %d-minute grid: use a shorter interval"
                          % (inst["label"], hm(inst["open_local"]), step // 60))
    out, t = [], inst["open_utc"]
    delta = datetime.timedelta(seconds=step)
    while t < inst["close_utc"]:
        if not any(b0 <= t < b1 for b0, b1 in inst["breaks_utc"]):
            out.append(t)
        t += delta
    return out


def _moved(inst, local_dt):
    """An absolute time that falls after an early close moves up by the time the session lost."""
    if inst["early"] and local_dt >= inst["close_local"]:
        return local_dt - (inst["normal_close_local"] - inst["close_local"])
    return local_dt


def windows(inst, cfg=None, range_minutes=None):
    """When the opening range ends, the first and last time for a new entry, and the
    flat-by time, for one session instance. Naive UTC plus local labels.
      range_minutes       --or-minutes, else config sessions.<name>.range, else the session's
      no_entries_before   config sessions.<name>.no_entries_before (local), else the range end
      no_entries_after    config sessions.<name>.no_entries_after, else close - entry_cutoff_minutes
      flat_by             config sessions.<name>.flat_by, else close - flat_by_minutes"""
    c = load_config(None) if cfg is None else cfg
    s = inst["def"]
    rng = int(range_minutes if range_minutes is not None else s["range"])
    if rng <= 0:
        raise TraderError("the opening range must be at least one bar long")
    tz = inst["tz"]
    base = datetime.datetime.combine(inst["open_local"].date(), datetime.time())
    range_end = inst["open_local"] + datetime.timedelta(minutes=rng)
    if range_end >= inst["close_local"]:
        raise TraderError("a %d-minute range does not end before the %s closes" % (rng, inst["label"]))

    def absolute(key):
        v = s.get(key)
        if not v:
            return None
        t = base + datetime.timedelta(minutes=parse_hhmm(v, "sessions.%s.%s" % (inst["session"], key)))
        if t < inst["open_local"]:
            t += datetime.timedelta(days=1)
        return _moved(inst, t)
    before = absolute("no_entries_before") or range_end
    after = absolute("no_entries_after") or (
        inst["close_local"] - datetime.timedelta(minutes=int(c.get("entry_cutoff_minutes", 30))))
    flat = absolute("flat_by") or (inst["close_local"] - datetime.timedelta(minutes=int(c.get("flat_by_minutes", 5))))
    before = max(before, range_end)
    flat = min(flat, inst["close_local"])
    if after > flat:
        after = flat
    out = {"range_minutes": rng}
    for k, v in (("range_end", range_end), ("no_entries_before", before), ("no_entries_after", after),
                 ("flat_by", flat)):
        out[k] = to_utc(tz, v)
        out[k + "_local"] = v
    return out


def day_label(d):
    return "%s %s" % (d.strftime("%a"), d.isoformat())


# ================================================================ instruments

def _digits(tick):
    exp = Decimal(str(tick)).normalize().as_tuple().exponent
    return max(0, -exp)


def _mk(symbol, name, cls, kind, feed, base, quote, tick, pip, pip_label, contract, lot_step, session,
        leverage, spread, unit="lot", min_lot=None, currencies=None, cot=None, aliases=(), volume=True):
    return {"symbol": symbol, "name": name, "class": cls, "kind": kind, "feed": feed, "base": base,
            "quote": quote, "tick": tick, "pip": pip, "pip_label": pip_label, "digits": _digits(tick),
            "contract": contract, "lot_step": lot_step, "min_lot": min_lot if min_lot is not None else lot_step,
            "unit": unit, "session": session, "leverage": leverage, "spread": spread,
            "currencies": list(currencies or [quote]), "cot": cot[0] if cot else None,
            "cot_sign": cot[1] if cot else None, "aliases": list(aliases),
            "gap_tolerance": 3 if cls in ("forex", "crypto") else 0, "volume": volume}


# (pair, typical spread in pips, ESMA retail leverage). ESMA: a "major" pair is any two of
# USD, EUR, JPY, GBP, CAD and CHF (30:1); every other pair is 20:1.
_FX = [
    ("EURUSD", 0.8, 30), ("GBPUSD", 1.2, 30), ("USDJPY", 1.0, 30), ("USDCHF", 1.4, 30), ("USDCAD", 1.4, 30),
    ("AUDUSD", 1.0, 20), ("NZDUSD", 1.6, 20),
    ("EURGBP", 1.2, 30), ("EURJPY", 1.6, 30), ("GBPJPY", 2.5, 30), ("EURCHF", 1.8, 30), ("GBPCHF", 2.6, 30),
    ("CHFJPY", 2.4, 30), ("CADJPY", 2.2, 30), ("EURCAD", 2.4, 30), ("GBPCAD", 3.2, 30), ("CADCHF", 2.4, 30),
    ("AUDJPY", 1.8, 20), ("NZDJPY", 2.4, 20), ("EURAUD", 2.2, 20), ("GBPAUD", 3.0, 20), ("AUDNZD", 2.6, 20),
    ("AUDCAD", 2.2, 20), ("AUDCHF", 2.2, 20), ("EURNZD", 3.5, 20), ("GBPNZD", 4.5, 20), ("NZDCAD", 3.0, 20),
    ("NZDCHF", 3.0, 20),
    ("USDZAR", 90, 20), ("USDMXN", 60, 20), ("USDTRY", 250, 20), ("USDSEK", 40, 20), ("USDNOK", 40, 20),
    ("USDSGD", 2.5, 20), ("USDHKD", 3.0, 20), ("USDCNH", 6.0, 20), ("USDPLN", 30, 20), ("EURNOK", 45, 20),
    ("EURSEK", 45, 20), ("EURPLN", 30, 20), ("EURTRY", 400, 20), ("EURZAR", 120, 20), ("GBPZAR", 150, 20),
]
# CFTC contract market codes (Legacy COT) and the sign that maps a long futures position
# onto the pair: +1 when the futures currency is the pair's base, -1 when it is the quote.
_FX_COT = {"EURUSD": ("099741", 1), "GBPUSD": ("096742", 1), "USDJPY": ("097741", -1),
           "USDCHF": ("092741", -1), "USDCAD": ("090741", -1), "AUDUSD": ("232741", 1),
           "NZDUSD": ("112741", 1), "USDMXN": ("095741", -1), "USDZAR": ("122741", -1)}
_FX_NAMES = {"USD": "US dollar", "EUR": "euro", "JPY": "yen", "GBP": "pound", "CHF": "franc", "CAD": "Canadian dollar",
             "AUD": "Aussie", "NZD": "kiwi", "ZAR": "rand", "MXN": "peso", "TRY": "lira", "SEK": "krona",
             "NOK": "krone", "SGD": "Singapore dollar", "HKD": "HK dollar", "CNH": "offshore yuan", "PLN": "zloty"}


def _build_registry():
    reg = {}
    for pair, spread, lev in _FX:
        base, quote = pair[:3], pair[3:]
        pip = 0.01 if quote == "JPY" else 0.0001
        reg[pair] = _mk(pair, "%s / %s" % (_FX_NAMES.get(base, base), _FX_NAMES.get(quote, quote)), "forex",
                        "spot", pair + "=X", base, quote, pip / 10, pip, "pips", 100000, 0.01, "london", lev,
                        round(spread * pip, 6), currencies=[base, quote], cot=_FX_COT.get(pair),
                        aliases=["%s/%s" % (base, quote), "%s_%s" % (base, quote), pair + "=X"], volume=False)
    commodity = [
        # symbol, name, feed, base, tick, pip, pip_label, contract (units per lot), session, leverage, spread, cot, aliases
        ("XAUUSD", "Gold spot (CFD)", "GC=F", "XAU", 0.01, 0.1, "pips", 100, "comex", 20, 0.25, ("088691", 1),
         ["GOLD", "XAU/USD", "XAU_USD"]),
        ("XAGUSD", "Silver spot (CFD)", "SI=F", "XAG", 0.001, 0.01, "pips", 5000, "comex", 10, 0.025,
         ("084691", 1), ["SILVER", "XAG/USD", "XAG_USD"]),
        ("XPTUSD", "Platinum (CFD)", "PL=F", "XPT", 0.01, 0.1, "pips", 100, "comex", 10, 1.0, ("076651", 1),
         ["PLATINUM", "XPT/USD"]),
        ("XPDUSD", "Palladium (CFD)", "PA=F", "XPD", 0.01, 0.1, "pips", 100, "comex", 10, 2.0, ("075651", 1),
         ["PALLADIUM", "XPD/USD"]),
        ("USOIL", "WTI crude oil (CFD)", "CL=F", "WTI", 0.01, 0.01, "ticks", 1000, "nymex", 10, 0.03,
         ("067651", 1), ["WTI", "CRUDE", "XTIUSD", "WTICO_USD", "USCRUDE"]),
        ("UKOIL", "Brent crude oil (CFD)", "BZ=F", "BRENT", 0.01, 0.01, "ticks", 1000, "nymex", 10, 0.04, None,
         ["BRENT", "XBRUSD", "BCO_USD", "UKBRENT"]),
        ("NATGAS", "Natural gas (CFD)", "NG=F", "NG", 0.001, 0.001, "ticks", 10000, "nymex", 10, 0.005,
         ("023651", 1), ["XNGUSD", "NGAS", "NATURALGAS"]),
        ("COPPER", "Copper (CFD)", "HG=F", "HG", 0.0005, 0.0005, "ticks", 25000, "comex_copper", 10, 0.002,
         ("085692", 1), ["XCUUSD", "HG"]),
    ]
    for sym, name, feed, base, tick, pip, lab, contract, sess, lev, spread, cot, al in commodity:
        reg[sym] = _mk(sym, name, "commodity", "cfd", feed, base, "USD", tick, pip, lab, contract, 0.01, sess,
                       lev, spread, cot=cot, aliases=al)
    futures = [
        # symbol, name, feed, class, base, quote, tick, pip, pip_label, $ per 1.0 price, session, leverage, cot
        ("ES", "E-mini S&P 500 futures", "ES=F", "index", "SPX", "USD", 0.25, 1.0, "points", 50, "us_cash", 15, "13874A"),
        ("MES", "Micro E-mini S&P 500", "MES=F", "index", "SPX", "USD", 0.25, 1.0, "points", 5, "us_cash", 15, None),
        ("NQ", "E-mini Nasdaq-100 futures", "NQ=F", "index", "NDX", "USD", 0.25, 1.0, "points", 20, "us_cash", 15, "209742"),
        ("MNQ", "Micro E-mini Nasdaq-100", "MNQ=F", "index", "NDX", "USD", 0.25, 1.0, "points", 2, "us_cash", 15, None),
        ("YM", "E-mini Dow ($5) futures", "YM=F", "index", "DJI", "USD", 1.0, 1.0, "points", 5, "us_cash", 15, "124603"),
        ("MYM", "Micro E-mini Dow", "MYM=F", "index", "DJI", "USD", 1.0, 1.0, "points", 0.5, "us_cash", 15, None),
        ("RTY", "E-mini Russell 2000 futures", "RTY=F", "index", "RUT", "USD", 0.1, 1.0, "points", 50, "us_cash", 12, "239742"),
        ("M2K", "Micro E-mini Russell 2000", "M2K=F", "index", "RUT", "USD", 0.1, 1.0, "points", 5, "us_cash", 12, None),
        ("GC", "Gold futures (100 oz)", "GC=F", "commodity", "XAU", "USD", 0.1, 0.1, "ticks", 100, "comex", 12, "088691"),
        ("MGC", "Micro gold (10 oz)", "MGC=F", "commodity", "XAU", "USD", 0.1, 0.1, "ticks", 10, "comex", 12, None),
        ("SI", "Silver futures (5,000 oz)", "SI=F", "commodity", "XAG", "USD", 0.005, 0.005, "ticks", 5000, "comex", 8, "084691"),
        ("SIL", "Micro silver (1,000 oz)", "SIL=F", "commodity", "XAG", "USD", 0.005, 0.005, "ticks", 1000, "comex", 8, None),
        ("HG", "Copper futures", "HG=F", "commodity", "HG", "USD", 0.0005, 0.0005, "ticks", 25000, "comex_copper", 10, "085692"),
        ("CL", "WTI crude futures", "CL=F", "commodity", "WTI", "USD", 0.01, 0.01, "ticks", 1000, "nymex", 8, "067651"),
        ("MCL", "Micro WTI crude", "MCL=F", "commodity", "WTI", "USD", 0.01, 0.01, "ticks", 100, "nymex", 8, None),
        ("NG", "Henry Hub natural gas futures", "NG=F", "commodity", "NG", "USD", 0.001, 0.001, "ticks", 10000, "nymex", 6, "023651"),
        ("ZC", "Corn futures (cents/bu)", "ZC=F", "commodity", "CORN", "USD", 0.25, 0.25, "ticks", 50, "cbot", 15, "002602"),
        ("ZW", "Wheat futures (cents/bu)", "ZW=F", "commodity", "WHEAT", "USD", 0.25, 0.25, "ticks", 50, "cbot", 12, "001602"),
        ("ZS", "Soybean futures (cents/bu)", "ZS=F", "commodity", "SOY", "USD", 0.25, 0.25, "ticks", 50, "cbot", 15, "005602"),
        ("6E", "Euro FX futures", "6E=F", "forex", "EUR", "USD", 0.00005, 0.0001, "pips", 125000, "london", 25, "099741"),
        ("6B", "British pound futures", "6B=F", "forex", "GBP", "USD", 0.0001, 0.0001, "pips", 62500, "london", 25, "096742"),
        ("6J", "Japanese yen futures", "6J=F", "forex", "JPY", "USD", 0.0000005, 0.000001, "pips", 12500000, "tokyo", 25, "097741"),
        ("6A", "Australian dollar futures", "6A=F", "forex", "AUD", "USD", 0.00005, 0.0001, "pips", 100000, "sydney", 25, "232741"),
        ("6C", "Canadian dollar futures", "6C=F", "forex", "CAD", "USD", 0.00005, 0.0001, "pips", 100000, "ny", 25, "090741"),
        ("6S", "Swiss franc futures", "6S=F", "forex", "CHF", "USD", 0.00005, 0.0001, "pips", 125000, "london", 25, "092741"),
        ("BTC", "CME Bitcoin futures (5 BTC)", "BTC=F", "crypto", "BTC", "USD", 5.0, 5.0, "points", 5, "us_cash", 2.5, "133741"),
        ("MBT", "CME Micro Bitcoin (0.1 BTC)", "MBT=F", "crypto", "BTC", "USD", 5.0, 5.0, "points", 0.1, "us_cash", 2.5, None),
    ]
    for sym, name, feed, cls, base, quote, tick, pip, lab, mult, sess, lev, cot in futures:
        cur = [quote] if cls != "forex" else [base, quote]
        reg[sym] = _mk(sym, name, cls, "future", feed, base, quote, tick, pip, lab, mult, 1, sess, lev,
                       tick * 2, unit="contract", min_lot=1, currencies=cur, cot=(cot, 1) if cot else None,
                       aliases=[feed])
    indices = [
        # symbol, name, feed, quote, tick, session, leverage, spread (points), currencies, cot, aliases
        ("US500", "S&P 500", "^GSPC", "USD", 0.01, "us_cash", 20, 0.5, ["USD"], "13874A",
         ["SPX", "SPX500", "SP500", "S&P500", "SPX500_USD", "US500CASH"]),
        ("US100", "Nasdaq-100", "^NDX", "USD", 0.01, "us_cash", 20, 1.0, ["USD"], "209742",
         ["NAS100", "NDX", "USTEC", "NASDAQ", "NAS100_USD"]),
        ("US30", "Dow Jones Industrial Average", "^DJI", "USD", 0.01, "us_cash", 20, 2.0, ["USD"], "124603",
         ["DJ30", "DJI", "WS30", "DOW", "US30_USD"]),
        ("US2000", "Russell 2000", "^RUT", "USD", 0.01, "us_cash", 10, 0.3, ["USD"], "239742",
         ["RUT", "RUSSELL", "US2000_USD"]),
        ("GER40", "DAX 40", "^GDAXI", "EUR", 0.01, "xetra", 20, 1.0, ["EUR"], None,
         ["DAX", "DE40", "GER30", "DE30", "DE30_EUR"]),
        ("UK100", "FTSE 100", "^FTSE", "GBP", 0.01, "lse", 20, 1.0, ["GBP"], None, ["FTSE", "UK100_GBP"]),
        ("FRA40", "CAC 40", "^FCHI", "EUR", 0.01, "euronext", 20, 1.0, ["EUR"], None, ["CAC", "FR40", "FR40_EUR"]),
        ("EU50", "Euro Stoxx 50", "^STOXX50E", "EUR", 0.01, "xetra", 20, 1.5, ["EUR"], None,
         ["STOXX50", "ESTX50", "EU50_EUR"]),
        ("JPN225", "Nikkei 225", "^N225", "JPY", 0.01, "tse", 20, 8.0, ["JPY"], None,
         ["NIKKEI", "JP225", "N225", "JP225_USD"]),
        ("HK50", "Hang Seng", "^HSI", "HKD", 0.01, "hkex", 10, 6.0, ["HKD", "CNY"], None, ["HSI", "HK33", "HK33_HKD"]),
        ("AUS200", "S&P/ASX 200", "^AXJO", "AUD", 0.01, "asx", 20, 1.0, ["AUD"], None, ["ASX200", "AU200", "AU200_AUD"]),
    ]
    for sym, name, feed, quote, tick, sess, lev, spread, cur, cot, al in indices:
        reg[sym] = _mk(sym, name + " (cash index / CFD)", "index", "cfd", feed, sym, quote, tick, 1.0, "points",
                       1, 0.1, sess, lev, spread, currencies=cur, cot=(cot, 1) if cot else None, aliases=al)
    crypto = [
        # symbol, name, feed, tick, pip, lot step (coins), spread, cot
        ("BTCUSD", "Bitcoin", "BTC-USD", 0.01, 1.0, 0.0001, 10.0, ("133741", 1), ["BTC", "XBTUSD", "BTC/USD", "BTCUSDT"]),
        ("ETHUSD", "Ether", "ETH-USD", 0.01, 0.1, 0.001, 1.0, None, ["ETH", "ETH/USD", "ETHUSDT"]),
        ("SOLUSD", "Solana", "SOL-USD", 0.01, 0.01, 0.01, 0.05, None, ["SOL", "SOL/USD", "SOLUSDT"]),
        ("XRPUSD", "XRP", "XRP-USD", 0.0001, 0.0001, 1, 0.001, None, ["XRP", "XRP/USD", "XRPUSDT"]),
        ("BNBUSD", "BNB", "BNB-USD", 0.01, 0.1, 0.01, 0.3, None, ["BNB", "BNB/USD", "BNBUSDT"]),
        ("ADAUSD", "Cardano", "ADA-USD", 0.0001, 0.0001, 1, 0.0005, None, ["ADA", "ADA/USD", "ADAUSDT"]),
        ("DOGEUSD", "Dogecoin", "DOGE-USD", 0.00001, 0.0001, 1, 0.0002, None, ["DOGE", "DOGE/USD", "DOGEUSDT"]),
        ("LTCUSD", "Litecoin", "LTC-USD", 0.01, 0.01, 0.01, 0.05, None, ["LTC", "LTC/USD", "LTCUSDT"]),
        ("AVAXUSD", "Avalanche", "AVAX-USD", 0.01, 0.01, 0.01, 0.03, None, ["AVAX", "AVAX/USD", "AVAXUSDT"]),
        ("LINKUSD", "Chainlink", "LINK-USD", 0.001, 0.001, 0.1, 0.01, None, ["LINK", "LINK/USD", "LINKUSDT"]),
        ("DOTUSD", "Polkadot", "DOT-USD", 0.001, 0.001, 0.1, 0.005, None, ["DOT", "DOT/USD", "DOTUSDT"]),
    ]
    for sym, name, feed, tick, pip, step, spread, cot, al in crypto:
        reg[sym] = _mk(sym, name, "crypto", "spot", feed, sym[:-3], "USD", tick, pip, "points", 1, step, "utc", 2,
                       spread, unit="coin", currencies=["USD"], cot=cot, aliases=al + [feed])
    return reg


INSTRUMENTS = _build_registry()


def _alias_index(reg):
    idx = {}
    for sym, inst in reg.items():
        idx[sym.upper()] = sym
        for a in inst.get("aliases") or []:
            idx.setdefault(str(a).upper(), sym)
        if inst.get("feed"):
            idx.setdefault(str(inst["feed"]).upper(), sym)
    return idx


def registry(cfg=None, extra_path=None):
    """The built-in registry plus trader/instruments.json and config "instruments" overrides."""
    reg = {k: dict(v) for k, v in INSTRUMENTS.items()}
    sources = []
    path = extra_path if extra_path is not None else os.path.join("trader", "instruments.json")
    if path and os.path.exists(path):
        doc = read_json(path, "instruments file")
        sources.append(doc.get("instruments", doc) if isinstance(doc, dict) else {})
    if cfg and isinstance(cfg.get("instruments"), dict):
        sources.append(cfg["instruments"])
    for src in sources:
        for sym, spec in src.items():
            if not isinstance(spec, dict):
                continue
            key = str(sym).upper()
            if key in reg:
                reg[key].update(spec)
            else:
                need = [k for k in ("class", "feed", "quote", "tick", "contract") if k not in spec]
                if need:
                    raise TraderError("custom instrument %s needs %s" % (key, ", ".join(need)))
                base = _mk(key, spec.get("name", key), spec["class"], spec.get("kind", "cfd"), spec["feed"],
                           spec.get("base", key), spec["quote"], spec["tick"], spec.get("pip", spec["tick"]),
                           spec.get("pip_label", "points"), spec["contract"], spec.get("lot_step", 0.01),
                           spec.get("session", "utc" if spec["class"] == "crypto" else "london"),
                           spec.get("leverage", 10), spec.get("spread", spec["tick"] * 2))
                base.update(spec)
                reg[key] = base
            inst = reg[key]
            inst["symbol"] = key
            inst["digits"] = _digits(inst["tick"])
            if inst["class"] not in CLASSES:
                raise TraderError("instrument %s has class %r; one of %s" % (key, inst["class"], ", ".join(CLASSES)))
    return reg


def resolve(symbol, cfg=None, reg=None):
    """'EUR/USD', 'eurusd', 'EURUSD=X', 'GOLD', 'BTC-USD' -> the instrument dict (a copy)."""
    reg = reg or registry(cfg)
    key = str(symbol or "").strip().upper()
    if not key:
        raise TraderError("no symbol given")
    idx = _alias_index(reg)
    if key in idx:
        return dict(reg[idx[key]])
    squash = re.sub(r"[^A-Z0-9]", "", key)
    if squash in idx:
        return dict(reg[idx[squash]])
    near = difflib.get_close_matches(key, list(reg), n=4, cutoff=0.6)
    raise TraderError("unknown instrument %r%s. See: python3 trader-core/tradercore.py instruments"
                      % (symbol, (" (did you mean %s?)" % ", ".join(near)) if near else ""))


def universe(classes=None, cfg=None, kinds=None):
    """Instruments of the given classes (default all), sorted by class then symbol."""
    reg = registry(cfg)
    want = set(classes or CLASSES)
    bad = want - set(CLASSES)
    if bad:
        raise TraderError("unknown class %s: use %s" % (", ".join(sorted(bad)), ", ".join(CLASSES)))
    out = [v for v in reg.values() if v["class"] in want and (not kinds or v["kind"] in kinds)]
    return sorted(out, key=lambda i: (CLASSES.index(i["class"]), i["kind"] != "spot" and i["kind"] != "cfd",
                                      i["symbol"]))


def parse_classes(text):
    if not text:
        return None
    out = []
    for p in re.split(r"[,\s]+", str(text).lower()):
        if not p:
            continue
        p = {"fx": "forex", "currencies": "forex", "commodities": "commodity", "metals": "commodity",
             "energy": "commodity", "indices": "index", "indexes": "index", "cryptos": "crypto"}.get(p, p)
        if p not in CLASSES:
            raise TraderError("unknown class %r: use forex, commodity, index or crypto" % p)
        out.append(p)
    return out


# ================================================================ brokers

BROKERS = {
    "paper": {"label": "paper (no broker)", "classes": CLASSES, "kinds": ("spot", "cfd", "future"),
              "short": True, "bracket": True},
    "oanda": {"label": "OANDA", "classes": ("forex", "commodity", "index"), "kinds": ("spot", "cfd"),
              "short": True, "bracket": True},
    "alpaca": {"label": "Alpaca (crypto spot)", "classes": ("crypto",), "kinds": ("spot",), "short": False,
               "bracket": False, "max_leverage": 1},
    "mt5": {"label": "MetaTrader 5", "classes": CLASSES, "kinds": ("spot", "cfd"), "short": True, "bracket": True},
    "ctrader": {"label": "cTrader", "classes": CLASSES, "kinds": ("spot", "cfd"), "short": True, "bracket": True},
    "ibkr": {"label": "Interactive Brokers", "classes": CLASSES, "kinds": ("spot", "cfd", "future"),
             "short": True, "bracket": True},
}


def broker_profile(cfg):
    name = str((cfg or {}).get("broker") or "paper").lower()
    if name not in BROKERS:
        raise TraderError("unknown broker %r in the config: one of %s" % (name, ", ".join(sorted(BROKERS))))
    return dict(BROKERS[name], name=name)


# ================================================================ config

DEFAULTS = {
    "account_currency": "USD",
    "balance": None,                   # the account you size against (or trader/portfolio.json)
    "timezone": "UTC",                 # how times print; sessions keep their own zones
    "broker": "paper",
    "paper": True,
    "max_loss_per_trade": 50,          # account currency, at the stop
    "max_daily_loss": 150,
    "max_trades_per_day": 3,
    "max_consecutive_losses": 3,       # losses in a row today (trader/journal.csv) before entries pause
    "max_orders_per_day": 10,
    "min_reward_risk": 1.0,
    "require_stop": True,
    "max_account_leverage": 10,        # total notional / equity after the order
    "max_margin_use_pct": 50,          # margin in use / equity after the order
    "max_currency_exposure_x": 10,     # net exposure in any one currency / equity
    "max_position_notional": None,
    "allowed_classes": list(CLASSES),
    "allow_short": True,
    "allow_futures": True,
    "blocked": [],
    "leverage": {},                    # per class or symbol caps under the broker's, e.g. {"crypto": 1}
    "news_blackout_minutes": 30,
    "news_blackout_impact": ["High"],
    "entry_cutoff_minutes": 30,        # no new entries this close to the session's close
    "flat_by_minutes": 5,              # out this long before the close, win or lose
    "sessions": {},                    # {"london": {"range": 60, "no_entries_after": "15:00", "flat_by": "16:30"}}
    "instruments": {},                 # {"XAUUSD": {"contract": 100, "broker_symbol": "XAUUSD.m"}}
    "rates": {},                       # manual conversion rates, e.g. {"USDJPY": 154.2}
    "symbol_suffix": "",
}
LEGACY_KEYS = {"max_loss_per_trade_usd": "max_loss_per_trade", "max_daily_loss_usd": "max_daily_loss",
               "budget": "balance", "max_order_usd": "max_position_notional"}


def load_config(path="trader/config.json"):
    cfg = dict(DEFAULTS)
    cfg["sessions"], cfg["instruments"], cfg["rates"], cfg["leverage"] = {}, {}, {}, {}
    if path and os.path.exists(path):
        doc = read_json(path, "config")
        if not isinstance(doc, dict):
            raise TraderError("%s is not a JSON object" % path)
        for old, new in LEGACY_KEYS.items():
            if old in doc and new not in doc:
                doc[new] = doc[old]
        cfg.update(doc)
    cfg["account_currency"] = str(cfg.get("account_currency") or "USD").upper()
    cfg["timezone"] = zone_name(cfg.get("timezone") or "UTC")
    return cfg


def leverage_cap(inst, cfg):
    """The leverage you may use on one instrument: the smallest of the instrument's cap
    (ESMA retail, or the exchange margin for futures), the broker's and your own
    config "leverage" by symbol or class."""
    caps = [float(inst.get("leverage") or 1)]
    prof = broker_profile(cfg)
    if prof.get("max_leverage"):
        caps.append(float(prof["max_leverage"]))
    own = (cfg or {}).get("leverage") or {}
    for k in (inst["symbol"], inst["class"]):
        if own.get(k):
            caps.append(float(own[k]))
    return max(1.0, min(caps))


# ================================================================ files

def read_json(path, what="file", required=True):
    if not path or not os.path.exists(path):
        if required:
            raise TraderError("no %s at %s" % (what, path))
        return None
    try:
        if str(path).endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                return json.load(fh)
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except ValueError as e:
        raise TraderError("%s is not valid JSON: %s" % (path, e))


def write_json(path, doc, indent=2):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=indent)
        fh.write("\n")
    os.replace(tmp, path)


def read_text(path):
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return fh.read()
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ================================================================ network and Yahoo

def http_get(url, timeout=20, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    h.update(headers or {})
    if OPENER is not None:
        return OPENER(url, timeout, h)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def yahoo_get(path):
    """GET a Yahoo Finance path: query2 first, query1 when query2 answers 429 or 5xx.
    An HTTP 429 gets one retry after BACKOFF seconds. Yahoo's JSON error bodies
    (unknown symbol) are returned for the caller to explain."""
    last = "no answer"
    for host in YAHOO_HOSTS:
        url = "https://%s.finance.yahoo.com%s" % (host, path)
        for attempt in (0, 1):
            try:
                return http_get(url)
            except urllib.error.HTTPError as e:
                code, body = e.code, ""
                try:
                    if 400 <= code < 500 and code != 429:
                        body = e.read().decode("utf-8", "replace")
                except Exception:
                    body = ""
                finally:
                    e.close()
                last = "HTTP %d" % code
                if code == 429 and attempt == 0:
                    SLEEP(BACKOFF)
                    continue
                if code == 429 or code >= 500:
                    break
                if body.strip().startswith("{"):
                    return body
                raise TraderError("Yahoo answered HTTP %d for %s" % (code, path.split("?")[0]))
            except urllib.error.URLError as e:
                last = "could not connect: %s" % (e.reason,)
                break
            except OSError as e:
                last = "network error: %s" % (e,)
                break
    raise TraderError("Yahoo did not answer (%s on query2 and query1): wait a minute and try again" % last)


def chart_path(feed, rng, interval):
    return "/v8/finance/chart/%s?range=%s&interval=%s" % (urllib.parse.quote(feed, safe="=-"), rng, interval)


def chart_range(days_back, interval):
    """The smallest Yahoo range holding a session `days_back` calendar days ago."""
    if days_back <= 0:
        return "1d" if interval != "1m" else "1d"
    if days_back <= 4:
        return "5d"
    if interval == "1m":
        if days_back <= 6:
            return "7d"
        raise TraderError("Yahoo keeps 1-minute bars for about a week: use --interval 5m")
    if days_back <= 28:
        return "1mo"
    if days_back <= 58:
        return "60d"
    raise TraderError("Yahoo keeps 5- and 15-minute bars for about 60 days: that day is too far back")


def parse_chart(text_or_doc, feed=""):
    """Yahoo v8 chart JSON -> {feed, meta, bars [{t,o,h,l,c,v}], prev_close, data_time, granularity}.
    Bars without a close are dropped; a missing open/high/low falls back to the close."""
    try:
        doc = json.loads(text_or_doc) if isinstance(text_or_doc, str) else text_or_doc
        chart = doc["chart"]
    except (ValueError, KeyError, TypeError):
        raise TraderError("Yahoo returned something unexpected for %s" % feed)
    res = chart.get("result")
    if not res:
        err = chart.get("error") or {}
        raise TraderError("Yahoo has no data for %s: %s" % (feed, err.get("description") or "unknown symbol"))
    r = res[0] or {}
    meta = r.get("meta") or {}
    q = ((r.get("indicators") or {}).get("quote") or [{}])[0] or {}

    def col(k, i):
        arr = q.get(k) or []
        return arr[i] if i < len(arr) else None
    bars = {}
    for i, t in enumerate(r.get("timestamp") or []):
        c = col("close", i)
        if t is None or c is None:
            continue
        o, h, lo = col("open", i), col("high", i), col("low", i)
        c = float(c)
        o = c if o is None else float(o)
        h = max(c, o) if h is None else float(h)
        lo = min(c, o) if lo is None else float(lo)
        bars[int(t)] = {"t": int(t), "o": o, "h": h, "l": lo, "c": c, "v": float(col("volume", i) or 0)}
    return {"feed": str(meta.get("symbol") or feed), "meta": meta, "bars": [bars[k] for k in sorted(bars)],
            "prev_close": meta.get("previousClose") or meta.get("chartPreviousClose"),
            "data_time": meta.get("regularMarketTime"), "granularity": meta.get("dataGranularity")}


def offline_file(path, inst, tag=None):
    """A saved chart: PATH itself, or PATH/<SYMBOL>[-<tag>].json(.gz) / <FEED>.json(.gz) in a folder."""
    if os.path.isfile(path):
        return path
    if not os.path.isdir(path):
        raise TraderError("no offline file or folder at %s" % path)
    feed = re.sub(r"[^A-Za-z0-9=\-]", "", inst.get("feed") or "")
    names = []
    for stem in (inst["symbol"], feed):
        if tag:
            names += ["%s-%s.json.gz" % (stem, tag), "%s-%s.json" % (stem, tag)]
        names += ["%s.json.gz" % stem, "%s.json" % stem]
    for n in names:
        p = os.path.join(path, n)
        if os.path.exists(p):
            return p
    for stem in (inst["symbol"], feed):
        hits = sorted(f for f in os.listdir(path) if f.startswith(stem + "-") and f.endswith((".json", ".json.gz")))
        if hits:
            return os.path.join(path, hits[0])
    raise TraderError("no offline chart for %s in %s (want %s)" % (inst["symbol"], path, names[0]))


def get_chart(inst, interval="5m", rng="1d", offline=None, tag=None):
    """Bars for one instrument from Yahoo or a saved file, checked to be the right feed and bar size."""
    if interval not in INTERVALS:
        raise TraderError("--interval is %s" % ", ".join(INTERVALS))
    if offline:
        f = offline_file(offline, inst, tag)
        try:
            text = read_text(f)
        except (OSError, ValueError) as e:
            raise TraderError("could not read %s: %s" % (f, e))
        source = "offline:" + os.path.basename(f)
    else:
        text = yahoo_get(chart_path(inst["feed"], rng, interval))
        source = "yahoo"
    ch = parse_chart(text, inst["feed"])
    got = str(ch["meta"].get("symbol") or "").upper()
    if got and got != str(inst["feed"]).upper():
        raise TraderError("the chart holds %s, not %s (%s)" % (got, inst["feed"], inst["symbol"]))
    if ch["granularity"] and ch["granularity"] != interval:
        raise TraderError("%s has %s bars, not %s: use --interval %s" % (inst["symbol"], ch["granularity"], interval,
                                                                       ch["granularity"]))
    ch["source"] = source
    ch["symbol"] = inst["symbol"]
    return ch


def session_bars(chart, inst_session, step, now=None, settle=SETTLE):
    """The bars of one session instance on the `step` grid, by slot.

    Returns {"bars": closed bars (oldest first, each with slot/start/end), "pending": a
    bar closed by the clock that Yahoo has not caught up to, "forming": the bar in
    progress, "slots": the expected bar starts}. A bar off the grid (the live tick) is
    dropped; with `now`, a bar counts once start + step <= now and Yahoo's last trade
    is at or after its close (or a later bar exists, or `settle` seconds passed)."""
    sl = slots(inst_session, step)
    index = {ts_of(t): i for i, t in enumerate(sl)}
    by = {}
    for b in chart["bars"]:
        if b["t"] % step:
            continue
        i = index.get(b["t"])
        if i is None:
            continue
        start = utc_of(b["t"])
        by[i] = dict(b, slot=i, start=start, end=start + datetime.timedelta(seconds=step))
    dt = chart.get("data_time")
    now_ts = ts_of(now) if now is not None else None
    keys = sorted(by)
    top = keys[-1] if keys else -1
    bars, pending, forming = [], None, None
    for i in keys:
        b = by[i]
        end_ts = b["t"] + step
        if now_ts is None or end_ts <= now_ts:
            if now_ts is None or dt is None or dt >= end_ts or i < top or now_ts >= end_ts + settle:
                bars.append(b)
            else:
                pending = b
        elif b["t"] <= now_ts:
            forming = b
    return {"bars": bars, "pending": pending, "forming": forming, "slots": sl}


def fill_gaps(bars, upto_slot, tolerance):
    """Bars for slots 0..upto_slot with up to `tolerance` missing ones filled flat at the
    previous close (OTC feeds skip a quiet 5 minutes now and then). (bars, filled) or
    (None, missing) when too many are missing or the very first bar is."""
    by = {b["slot"]: b for b in bars}
    missing = [i for i in range(upto_slot + 1) if i not in by]
    if not missing:
        return [by[i] for i in range(upto_slot + 1)], 0
    if len(missing) > tolerance or 0 in missing:
        return None, len(missing)
    out = []
    for i in range(upto_slot + 1):
        if i in by:
            out.append(by[i])
        else:
            p = out[-1]
            step = p["end"] - p["start"]
            out.append({"t": p["t"] + int(step.total_seconds()), "o": p["c"], "h": p["c"], "l": p["c"], "c": p["c"],
                        "v": 0.0, "slot": i, "start": p["end"], "end": p["end"] + step, "filled": True})
    return out, len(missing)


# ================================================================ money and prices

def D(x, what="a number"):
    try:
        if isinstance(x, Decimal):
            return x
        if isinstance(x, float):
            return Decimal(repr(x))
        return Decimal(str(x).strip().lstrip("$").replace(",", ""))
    except (InvalidOperation, ValueError):
        raise TraderError("%s is not a number: %r" % (what, x))


_MODES = {"nearest": ROUND_HALF_UP, "down": ROUND_FLOOR, "up": ROUND_CEILING}


def to_tick(x, tick, how="nearest"):
    """Round a price to the instrument's tick: nearest (half up), down or up. Returns Decimal."""
    t = D(tick)
    q = (D(x) / t).quantize(Decimal(1), rounding=_MODES[how])
    return (q * t).quantize(t.normalize() if t.normalize().as_tuple().exponent < 0 else Decimal(1))


def stop_tick(x, tick, long):
    """A stop rounds AWAY from the entry: down for a long, up for a short."""
    return to_tick(x, tick, "down" if long else "up")


def fmt_price(x, inst):
    d = inst["digits"]
    return format(D(x).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP), "f") if d else \
        format(D(x).quantize(Decimal(1), rounding=ROUND_HALF_UP), "f")


def pips(distance, inst):
    return float(D(distance) / D(inst["pip"]))


def fmt_dist(distance, inst):
    """0.00125 on EURUSD -> '12.5 pips'; 14.75 on US500 -> '14.8 points'."""
    n = abs(pips(distance, inst))
    if n >= 1000:
        body = "{:,.0f}".format(n)
    elif abs(n * 10 - round(n * 10)) > 1e-6:
        body = "%.2f" % n
    else:
        body = "%.1f" % n
    return "%s %s" % (body, inst["pip_label"])


CCY_SIGN = {"USD": "$"}


def money(x, ccy="USD", cents=True):
    x = float(x)
    if ccy == "JPY":
        cents = False
    body = "{:,.2f}".format(abs(x)) if cents else "{:,.0f}".format(abs(x))
    sign = "-" if x < 0 else ""
    if ccy in CCY_SIGN:
        return "%s%s%s" % (sign, CCY_SIGN[ccy], body)
    return "%s%s %s" % (sign, body, ccy)


def floor_step(x, step):
    """Round a quantity DOWN to a whole number of steps (0.01 lots, 1 contract, 0.0001 BTC)."""
    s = D(step)
    return (D(x) / s).quantize(Decimal(1), rounding=ROUND_FLOOR) * s


def num(x):
    """Decimal or float -> '0.25', '1', '12.5' (no trailing zeros)."""
    d = D(x).normalize()
    s = format(d, "f")
    return s


def _rate(a, b, rates):
    for key, inv in ((a + b, False), (b + a, True)):
        for k in (key, key[:3] + "/" + key[3:], key[:3] + "_" + key[3:]):
            v = rates.get(k)
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            if v > 0:
                return 1.0 / v if inv else v
    return None


def conversion(frm, to, rates):
    """How many `to` one `frm` is worth, from rates like {"EURUSD": 1.16, "USDJPY": 154.2}:
    direct, inverse, or through USD. Raises with the rate it needs."""
    frm, to = str(frm).upper(), str(to).upper()
    if frm == to:
        return 1.0
    r = _rate(frm, to, rates or {})
    if r:
        return r
    if "USD" not in (frm, to):
        a, b = _rate(frm, "USD", rates or {}), _rate("USD", to, rates or {})
        if a and b:
            return a * b
    raise TraderError("need a %s/%s rate to convert %s into %s: quote it (alerts.py quote %s%s --write) or set "
                      "\"rates\": {\"%s%s\": ...} in trader/config.json" % (frm, to, frm, to, frm, to, frm, to))


def quote_to_account(inst, acct, rates, price=None):
    """Multiply an amount in the instrument's quote currency by this to get the account currency.
    USDJPY with a USD account uses its own price (1 / price) when no rate is given."""
    q = str(inst["quote"]).upper()
    if q == acct:
        return 1.0
    if inst["class"] == "forex" and str(inst["base"]).upper() == acct and price:
        r = _rate(q, acct, rates or {})
        return r if r else 1.0 / float(price)
    return conversion(q, acct, rates)


def rates_from(prices_doc=None, cfg=None, extra=None):
    """Conversion rates from trader/prices.json (our symbols), the config's "rates" and flags."""
    out = {}
    if isinstance(prices_doc, dict):
        for k, v in (prices_doc.get("prices") or {}).items():
            try:
                out[str(k).upper()] = float(v)
            except (TypeError, ValueError):
                pass
    for src in ((cfg or {}).get("rates") or {}, extra or {}):
        for k, v in src.items():
            try:
                out[str(k).upper().replace("/", "").replace("_", "")] = float(v)
            except (TypeError, ValueError):
                pass
    return out


def parse_rates(items):
    """['USDJPY=154.2', 'EURUSD=1.16'] -> dict."""
    out = {}
    for it in items or []:
        for part in str(it).split(","):
            if not part.strip():
                continue
            if "=" not in part:
                raise TraderError("--rate wants PAIR=RATE, like USDJPY=154.2, not %r" % part)
            k, v = part.split("=", 1)
            try:
                out[k.strip().upper().replace("/", "")] = float(v)
            except ValueError:
                raise TraderError("--rate %s is not a number" % part)
    return out


def exposure_of(inst, signed_units, notional_acct, acct):
    """{bucket: signed value in the account currency} for one position. A forex pair is
    long its base and short its quote; gold, an index or a coin is long its asset and
    short its quote currency. The account's own currency is left out: it is home."""
    sign = 1 if signed_units > 0 else -1
    out = {}
    for bucket, s in ((str(inst["base"]).upper(), sign), (str(inst["quote"]).upper(), -sign)):
        if bucket != acct:
            out[bucket] = out.get(bucket, 0.0) + s * notional_acct
    return out


def portfolio_positions(portfolio):
    """[{symbol, units (signed), avg_price}] from trader/portfolio.json."""
    out = []
    for p in (portfolio or {}).get("positions", []):
        sym = str(p.get("symbol") or p.get("ticker") or "").upper()
        if not sym:
            continue
        try:
            units = float(p.get("units", p.get("qty", p.get("shares", 0))))
            avg = float(p.get("avg_price", p.get("price", 0)) or 0)
        except (TypeError, ValueError):
            raise TraderError("portfolio position %s needs numbers for units and avg_price" % sym)
        if abs(units) > 1e-12:
            out.append({"symbol": sym, "units": units, "avg_price": avg})
    return out


def account_state(cfg, portfolio, rates, prices, reg=None):
    """Balance, equity, notional, margin and currency exposure of the account.
    No portfolio = a fresh account holding the config's "balance"."""
    acct = cfg["account_currency"]
    warnings = []
    if portfolio is None:
        bal = cfg.get("balance")
        if not bal:
            raise TraderError("no trader/portfolio.json and no \"balance\" in trader/config.json: nothing to size or "
                              "check against")
        balance, positions = float(bal), []
    else:
        b = portfolio.get("balance", portfolio.get("cash"))
        if b is None:
            raise TraderError("trader/portfolio.json needs a \"balance\" number")
        balance, positions = float(b), portfolio_positions(portfolio)
        if str(portfolio.get("currency") or acct).upper() != acct:
            raise TraderError("trader/portfolio.json is in %s but the config's account_currency is %s"
                              % (portfolio.get("currency"), acct))
    reg = reg or registry(cfg)
    st = {"currency": acct, "balance": balance, "positions": [], "notional": 0.0, "margin": 0.0, "upnl": 0.0,
          "exposure": {}, "warnings": warnings}
    for p in positions:
        inst = resolve(p["symbol"], cfg, reg)
        price = (prices or {}).get(inst["symbol"])
        if price is None:
            price = p["avg_price"]
            warnings.append("no price for %s: valued at its average price %s" % (inst["symbol"], price))
        conv = quote_to_account(inst, acct, rates, price)
        notional = abs(p["units"]) * price * conv
        margin = notional / leverage_cap(inst, cfg)
        upnl = (price - p["avg_price"]) * p["units"] * conv
        st["notional"] += notional
        st["margin"] += margin
        st["upnl"] += upnl
        for k, v in exposure_of(inst, p["units"], notional, acct).items():
            st["exposure"][k] = st["exposure"].get(k, 0.0) + v
        st["positions"].append(dict(p, price=price, notional=notional, margin=margin, upnl=upnl,
                                    **{"class": inst["class"]}))
    st["equity"] = balance + st["upnl"]
    return st


def held_units(state, symbol):
    return sum(p["units"] for p in state["positions"] if p["symbol"] == symbol)


def load_prices(doc):
    """trader/prices.json -> ({SYMBOL: price}, {SYMBOL: naive UTC time of the price or None})."""
    if not isinstance(doc, dict):
        return {}, {}
    prices = doc.get("prices", {})
    if not isinstance(prices, dict):
        return {}, {}
    out, times = {}, {}
    as_of = parse_utc(doc.get("as_of"))
    detail = doc.get("detail") or {}
    for s, p in prices.items():
        try:
            v = float(p)
        except (TypeError, ValueError):
            continue
        s = str(s).upper()
        out[s] = v
        d = detail.get(s) or {}
        times[s] = parse_utc(d.get("time")) or parse_utc(d.get("fetched")) or as_of
    return out, times


def fresh(price_times, sym, now_utc, minutes=15):
    """True when the price of `sym` is at most `minutes` old (and not from the future)."""
    t = (price_times or {}).get(sym)
    if t is None:
        return False
    age = (now_utc - t).total_seconds()
    return -60 <= age <= minutes * 60


def side_word(side):
    s = str(side or "").strip().lower()
    if s in ("buy", "long", "b", "l"):
        return "buy"
    if s in ("sell", "short", "s"):
        return "sell"
    raise TraderError("side is buy (long) or sell (short), not %r" % side)


def direction(side):
    return "long" if side_word(side) == "buy" else "short"


# ================================================================ the registry, printed

def _cmd_instruments(a):
    cfg = load_config(a.config)
    rows = universe(parse_classes(a.cls), cfg)
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    print("%-8s %-9s %-7s %-10s %-4s %-10s %-9s %-12s %-12s %s" % (
        "SYMBOL", "CLASS", "KIND", "FEED", "CCY", "TICK", "PIP", "CONTRACT", "SESSION", "LEV"))
    for i in rows:
        print("%-8s %-9s %-7s %-10s %-4s %-10s %-9s %-12s %-12s %g:1" % (
            i["symbol"], i["class"], i["kind"], i["feed"], i["quote"], num(i["tick"]), num(i["pip"]),
            "{:,}".format(i["contract"]) if i["contract"] >= 1 else num(i["contract"]), i["session"], i["leverage"]))
    print("%d instruments. Leverage = the ESMA retail cap (CFD and spot) or about the exchange margin (futures)."
          % len(rows))
    return 0


def _cmd_sessions(a):
    cfg = load_config(a.config)
    print("%-13s %-17s %-13s %-6s %s" % ("SESSION", "ZONE", "HOURS", "RANGE", "WHAT"))
    for k in sorted(SESSIONS):
        s = session_def(k, cfg)
        br = "".join(" (break %s-%s)" % b for b in s.get("breaks") or [])
        print("%-13s %-17s %-13s %-6s %s%s" % (k, s["tz"], "%s-%s" % (s["open"], s["close"]), "%dm" % int(s["range"]),
                                              s["label"], br))
    return 0


def _cmd_show(a):
    cfg = load_config(a.config)
    print(json.dumps(resolve(a.symbol, cfg), indent=2))
    return 0


def _cmd_clock(a):
    cfg = load_config(a.config)
    now = parse_now(a.now, cfg["timezone"])
    print("Clock: %s (%s)" % (stamp(now, cfg["timezone"]), iso(now)))
    for k in FX_SESSIONS + ("us_cash", "xetra", "lse", "tse", "comex", "nymex", "utc"):
        inst, phase = locate(k, now, cfg)
        if inst and phase == "open":
            print("  OPEN    %-12s until %s" % (k, stamp(inst["close_utc"], inst["tz"])))
        else:
            nxt = next_open(k, now, cfg)
            print("  closed  %-12s next opens %s" % (k, stamp(nxt["open_utc"], nxt["tz"]) if nxt else "unknown"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="tradercore: instruments, sessions and clocks of the GODMODE Trader.")
    ap.add_argument("--config", default="trader/config.json")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("instruments")
    p.add_argument("--class", dest="cls", help="forex, commodity, index, crypto (comma separated)")
    p.add_argument("--json", action="store_true")
    sub.add_parser("sessions")
    p = sub.add_parser("show")
    p.add_argument("symbol")
    p = sub.add_parser("clock")
    p.add_argument("--now")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        return {"instruments": _cmd_instruments, "sessions": _cmd_sessions, "show": _cmd_show,
                "clock": _cmd_clock}[a.cmd](a)
    except TraderError as e:
        print("tradercore.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
