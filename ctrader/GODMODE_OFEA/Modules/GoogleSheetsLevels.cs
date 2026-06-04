// GoogleSheetsLevels.cs
//
// HTTP bridge that pulls operator-curated key levels from a Google Sheets
// spreadsheet exported as CSV. Adapted from Frozen Tundra's google_sheets_
// importer.cpp pattern.
//
// Why this matters:
//   The brief's news_blackout.json schema lets the operator manually maintain
//   timed events. This module extends that pattern to *price* events — manual
//   support/resistance / weekly opens / IB high-low / market-profile single-
//   prints / round-number bands. The operator updates one Google Sheet, every
//   chart on every machine picks up the changes within 5 minutes.
//
// Required Google Sheet sharing: "Anyone with link can view".
// Required URL form (no /edit suffix):
//   https://docs.google.com/spreadsheets/d/{SHEET_ID}
//
// Expected sheet columns (in order):
//   Price, Price2 (optional, for rectangles), Note, Color, LineType, LineWidth, TextAlignment
//
// Example rows:
//   1.08920,,VAH-prior,blue,0,1,1
//   1.08300,,VAL-prior,blue,0,1,1
//   1.09000,,Round,gold,1,2,1
//   1.08600,1.08800,Range-IB,green,0,1,1
//
// cTrader requires AccessRights.FullAccess to use HttpClient. Without it the
// bridge returns gracefully (no levels) and logs to Print so the operator can
// promote the bot's permissions when ready.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Threading.Tasks;

namespace GodmodeOfea
{
    public sealed class ManualLevel
    {
        public double Price { get; set; }
        public double Price2 { get; set; }       // 0 if not a rectangle
        public string Note { get; set; } = string.Empty;
        public string Color { get; set; } = string.Empty;
        public int LineType { get; set; }        // 0 solid, 1 dash, 2 dot, 3 dashdot, 4 dashdotdot
        public int LineWidth { get; set; } = 1;
        public int TextAlignment { get; set; } = 1;
    }

    public sealed class GoogleSheetsLevels
    {
        private readonly string _baseUrl;       // https://docs.google.com/spreadsheets/d/{ID}
        private readonly double _refreshIntervalSec;
        private DateTime _lastFetch = DateTime.MinValue;
        private List<ManualLevel> _levels = new List<ManualLevel>();
        private string _lastError = string.Empty;

        public GoogleSheetsLevels(string baseUrl, double refreshIntervalSec = 300.0)
        {
            _baseUrl = baseUrl?.TrimEnd('/') ?? string.Empty;
            _refreshIntervalSec = refreshIntervalSec;
        }

        public async Task<bool> RefreshAsync(DateTime nowUtc)
        {
            if (string.IsNullOrEmpty(_baseUrl)) return false;
            if ((nowUtc - _lastFetch).TotalSeconds < _refreshIntervalSec) return false;
            _lastFetch = nowUtc;

            try
            {
                string url = _baseUrl + "/gviz/tq?tqx=out:csv";
                using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(15) })
                {
                    var resp = await http.GetAsync(url);
                    if (!resp.IsSuccessStatusCode)
                    {
                        // Translate HTTP status codes to operator-friendly errors
                        // so the dashboard shows useful context, not raw exceptions.
                        switch ((int)resp.StatusCode)
                        {
                            case 401:
                            case 403:
                                _lastError = "Permission denied — set the Sheet to 'Anyone with link can view'.";
                                break;
                            case 404:
                                _lastError = "Sheet not found (404) — check the URL/ID.";
                                break;
                            case 429:
                                _lastError = "Rate-limited by Google — increase RefreshIntervalSec.";
                                break;
                            default:
                                _lastError = $"HTTP {(int)resp.StatusCode} {resp.ReasonPhrase}";
                                break;
                        }
                        return false;
                    }
                    string body = await resp.Content.ReadAsStringAsync();
                    var fresh = ParseCsv(body);
                    _levels = fresh;
                    _lastError = string.Empty;
                    return true;
                }
            }
            catch (TaskCanceledException)
            {
                _lastError = "Network timeout (15s) — Google Sheets unreachable.";
                return false;
            }
            catch (HttpRequestException e)
            {
                _lastError = "Network error: " + e.Message;
                return false;
            }
            catch (Exception e)
            {
                _lastError = "Sheet parse failure: " + e.Message;
                return false;
            }
        }

        private static List<ManualLevel> ParseCsv(string body)
        {
            var inv = CultureInfo.InvariantCulture;
            var result = new List<ManualLevel>();
            using (var sr = new StringReader(body))
            {
                string line;
                while ((line = sr.ReadLine()) != null)
                {
                    var trimmed = line.Trim();
                    if (string.IsNullOrEmpty(trimmed)) continue;
                    // Google's gviz CSV wraps fields in quotes. Strip the leading/trailing quote and split
                    // on the canonical "," sentinel.
                    if (trimmed.StartsWith("\"") && trimmed.EndsWith("\""))
                        trimmed = trimmed.Substring(1, trimmed.Length - 2);
                    var fields = trimmed.Split(new[] { "\",\"" }, StringSplitOptions.None);
                    if (fields.Length == 0) continue;
                    if (!double.TryParse(fields[0], NumberStyles.Float, inv, out var price)) continue;
                    var lv = new ManualLevel { Price = price };
                    if (fields.Length > 1 && double.TryParse(fields[1], NumberStyles.Float, inv, out var p2)) lv.Price2 = p2;
                    if (fields.Length > 2) lv.Note = fields[2];
                    if (fields.Length > 3) lv.Color = fields[3];
                    if (fields.Length > 4 && int.TryParse(fields[4], out var lt)) lv.LineType = lt;
                    if (fields.Length > 5 && int.TryParse(fields[5], out var lw)) lv.LineWidth = lw;
                    if (fields.Length > 6 && int.TryParse(fields[6], out var ta)) lv.TextAlignment = ta;
                    result.Add(lv);
                }
            }
            return result;
        }

        public string LastError => _lastError;
        public IReadOnlyList<ManualLevel> Levels => _levels;

        // Find the closest manual level within tolerance — useful as a GATE 3 location bonus.
        public ManualLevel ClosestLevel(double price, double tolerance)
        {
            ManualLevel best = null;
            double bestDist = double.MaxValue;
            foreach (var lv in _levels)
            {
                double mid = lv.Price2 > 0 ? 0.5 * (lv.Price + lv.Price2) : lv.Price;
                double d = Math.Abs(mid - price);
                if (d < bestDist && d <= tolerance) { bestDist = d; best = lv; }
            }
            return best;
        }
    }
}
