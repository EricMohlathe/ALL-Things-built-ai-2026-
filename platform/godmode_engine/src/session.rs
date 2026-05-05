//! SAST session classifier + kill-zone tagging + sub-tier windows.
//!
//! Mirrors `OF_SessionGate.mqh` and `SessionGate.cs`. Brief §11.6, §22.6.
//! UTC→SAST offset defaults to +2 hours.

use chrono::{DateTime, Timelike, Utc};

use crate::common::{ActiveModel, Session, SubTier};

pub struct SessionGate {
    pub offset_hours: i32,
    pub ny_open_blackout_min: i32,
    pub allow_asian: bool,
    pub allow_ldn_open: bool,
    pub allow_ldn_main: bool,
    pub allow_ny_open: bool,
    pub allow_ny_main: bool,
    last_session: Session,
}

impl SessionGate {
    pub fn new(
        offset_hours: i32,
        ny_open_blackout_min: i32,
        allow_asian: bool,
        allow_ldn_open: bool,
        allow_ldn_main: bool,
        allow_ny_open: bool,
        allow_ny_main: bool,
    ) -> Self {
        Self {
            offset_hours,
            ny_open_blackout_min,
            allow_asian,
            allow_ldn_open,
            allow_ldn_main,
            allow_ny_open,
            allow_ny_main,
            last_session: Session::None,
        }
    }

    pub fn sast_minute(&self, now: DateTime<Utc>) -> i32 {
        let mut h = now.hour() as i32 + self.offset_hours;
        while h >= 24 {
            h -= 24;
        }
        while h < 0 {
            h += 24;
        }
        h * 60 + now.minute() as i32
    }

    pub fn classify(&self, now: DateTime<Utc>) -> (Session, i32) {
        let m = self.sast_minute(now);
        let s = if (120..600).contains(&m) {
            Session::Asian
        } else if (600..660).contains(&m) {
            Session::LdnOpen
        } else if (660..930).contains(&m) {
            Session::LdnMain
        } else if (930..1050).contains(&m) {
            Session::NyOpen
        } else if (1050..1260).contains(&m) {
            Session::NyMain
        } else {
            Session::After
        };
        (s, m)
    }

    pub fn is_session_enabled(&self, s: Session) -> bool {
        match s {
            Session::Asian => self.allow_asian,
            Session::LdnOpen => self.allow_ldn_open,
            Session::LdnMain => self.allow_ldn_main,
            Session::NyOpen => self.allow_ny_open,
            Session::NyMain => self.allow_ny_main,
            _ => false,
        }
    }

    pub fn in_ny_open_blackout(&self, now: DateTime<Utc>) -> bool {
        let m = self.sast_minute(now);
        m >= 930 && m < 930 + self.ny_open_blackout_min
    }

    pub fn sub_tier(&self, now: DateTime<Utc>) -> SubTier {
        let m = self.sast_minute(now);
        if (660..810).contains(&m) {
            SubTier::A
        } else if (810..930).contains(&m) {
            SubTier::B
        } else if (1050..1140).contains(&m) {
            SubTier::A
        } else if (1140..1260).contains(&m) {
            SubTier::B
        } else {
            SubTier::None
        }
    }

    pub fn approaching_ny_main_end(&self, now: DateTime<Utc>, minutes_before: i32) -> bool {
        let m = self.sast_minute(now);
        m >= 1260 - minutes_before && m < 1260
    }

    pub fn session_changed(&mut self, new_s: Session) -> bool {
        let changed = new_s != self.last_session;
        self.last_session = new_s;
        changed
    }

    pub fn model_for_session(&self, s: Session) -> ActiveModel {
        match s {
            Session::LdnMain => ActiveModel::M2MeanRev,
            Session::NyMain => ActiveModel::M1Trend,
            Session::LdnOpen => ActiveModel::M1Trend,
            _ => ActiveModel::None,
        }
    }

    /// True on a UTC-date rollover relative to a stored `last_day` value.
    /// Application owns the rolling state; this helper is just the
    /// comparator so day rollover happens at the same moment everywhere.
    pub fn is_new_day(now: DateTime<Utc>, last: DateTime<Utc>) -> bool {
        now.date_naive() != last.date_naive()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::TimeZone;

    fn utc(h: u32, m: u32) -> DateTime<Utc> {
        Utc.with_ymd_and_hms(2026, 5, 5, h, m, 0).unwrap()
    }

    #[test]
    fn classify_ldn_main() {
        let g = SessionGate::new(2, 20, true, true, true, true, true);
        // 09:30 UTC + 2h offset = 11:30 SAST = minute 690 → LDN_MAIN
        let (s, m) = g.classify(utc(9, 30));
        assert_eq!(s, Session::LdnMain);
        assert_eq!(m, 690);
    }

    #[test]
    fn ny_open_blackout_active() {
        let g = SessionGate::new(2, 20, true, true, true, true, true);
        // 13:35 UTC → 15:35 SAST = minute 935; within blackout 930..950
        assert!(g.in_ny_open_blackout(utc(13, 35)));
        // 13:55 UTC → 15:55 SAST = minute 955; outside blackout
        assert!(!g.in_ny_open_blackout(utc(13, 55)));
    }
}
