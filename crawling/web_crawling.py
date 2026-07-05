import json
import re
import ssl
import time
from datetime import datetime
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


BASE_URL = "https://www.bizinfo.go.kr"
LIST_URL = BASE_URL + "/sii/siia/selectSIIA200View.do?rows=15&cpage={page}"
OUTPUT_FILE = Path(__file__).with_name("index.html")
PAGE_START = 1
PAGE_END = 20


class BizInfoTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_tbody = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.current_cell = None
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tbody":
            self.in_tbody = True
        elif self.in_tbody and tag == "tr":
            self.in_row = True
            self.current_row = []
        elif self.in_row and tag == "td":
            self.in_cell = True
            self.current_cell = {"text": "", "href": ""}
        elif self.in_cell and tag == "a":
            href = attrs.get("href", "")
            if href:
                self.current_cell["href"] = urljoin(BASE_URL, href)

    def handle_endtag(self, tag):
        if tag == "td" and self.in_cell:
            self.current_cell["text"] = normalize_text(self.current_cell["text"])
            self.current_row.append(self.current_cell)
            self.current_cell = None
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            if self.current_row:
                self.rows.append(self.current_row)
            self.current_row = []
            self.in_row = False
        elif tag == "tbody":
            self.in_tbody = False

    def handle_data(self, data):
        if self.in_cell and self.current_cell is not None:
            self.current_cell["text"] += data


def normalize_text(value):
    return re.sub(r"\s+", " ", unescape(value)).strip()


def parse_period(period):
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", period)
    if len(dates) >= 2:
        return dates[0], dates[1]
    if len(dates) == 1:
        return dates[0], ""
    return "", ""


def fetch_page(page):
    url = LIST_URL.format(page=page)
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        },
    )
    context = ssl._create_unverified_context()
    with urlopen(request, timeout=20, context=context) as response:
        return response.read().decode("utf-8", "ignore")


def parse_page(html, page):
    parser = BizInfoTableParser()
    parser.feed(html)

    items = []
    for cells in parser.rows:
        if len(cells) < 8:
            continue

        period_from, period_to = parse_period(cells[3]["text"])
        items.append(
            {
                "page": page,
                "no": cells[0]["text"],
                "field": cells[1]["text"],
                "title": cells[2]["text"],
                "url": cells[2]["href"],
                "period": cells[3]["text"],
                "periodFrom": period_from,
                "periodTo": period_to,
                "ministry": cells[4]["text"],
                "agency": cells[5]["text"],
                "registeredAt": cells[6]["text"],
                "views": cells[7]["text"],
            }
        )
    return items


def collect_items():
    items = []
    for page in range(PAGE_START, PAGE_END + 1):
        print(f"{page}페이지 수집 중...")
        html = fetch_page(page)
        page_items = parse_page(html, page)
        print(f"  {len(page_items)}건")
        items.extend(page_items)
        time.sleep(0.25)
    return items


def unique_values(items, key):
    return sorted({item[key] for item in items if item.get(key)})


def build_html(items):
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_json = json.dumps(items, ensure_ascii=False)
    fields_json = json.dumps(unique_values(items, "field"), ensure_ascii=False)
    ministries_json = json.dumps(unique_values(items, "ministry"), ensure_ascii=False)
    agencies_json = json.dumps(unique_values(items, "agency"), ensure_ascii=False)

    template = r"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>기업마당 지원사업 공고 크롤링</title>
  <style>
    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: "Malgun Gothic", "Apple SD Gothic Neo", Arial, sans-serif;
      background: #f4f7fb;
      color: #17202a;
    }

    .app {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    .top-bar {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 18px;
      align-items: center;
      padding: 20px 28px;
      background: #1e2b36;
      color: #fff;
      border-bottom: 4px solid #2f9e8f;
    }

    h1 {
      margin: 0 0 7px;
      font-size: 26px;
      letter-spacing: 0;
    }

    .source {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      color: #d7e1e7;
      font-size: 14px;
    }

    .source a {
      color: #9ce7dc;
      text-decoration: none;
      font-weight: 700;
    }

    .summary-box {
      min-width: 190px;
      padding: 12px 16px;
      border: 1px solid #536a7f;
      border-radius: 6px;
      background: #2c4050;
      text-align: center;
    }

    .summary-box strong {
      display: block;
      margin-top: 3px;
      font-size: 24px;
    }

    .content {
      display: grid;
      gap: 16px;
      padding: 18px;
    }

    .filters {
      display: grid;
      grid-template-columns: repeat(6, minmax(140px, 1fr));
      gap: 12px;
      padding: 16px;
      border: 1px solid #d8e0e7;
      border-radius: 8px;
      background: #fff;
      box-shadow: 0 2px 8px rgba(23, 32, 42, 0.06);
    }

    .filter-field {
      display: grid;
      gap: 6px;
    }

    .filter-field.wide {
      grid-column: span 2;
    }

    label {
      color: #52616f;
      font-size: 13px;
      font-weight: 700;
    }

    input,
    select,
    button {
      width: 100%;
      min-height: 40px;
      border: 1px solid #c9d3dc;
      border-radius: 6px;
      background: #fff;
      color: #17202a;
      font: inherit;
    }

    input,
    select {
      padding: 0 10px;
    }

    button {
      cursor: pointer;
      border-color: #23766d;
      background: #23766d;
      color: #fff;
      font-weight: 700;
    }

    button.secondary {
      border-color: #8794a0;
      background: #f6f8fa;
      color: #22313f;
    }

    .table-panel {
      overflow: hidden;
      border: 1px solid #d8e0e7;
      border-radius: 8px;
      background: #fff;
      box-shadow: 0 2px 8px rgba(23, 32, 42, 0.06);
    }

    .table-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 14px 16px;
      border-bottom: 1px solid #e3e9ee;
      background: #fbfcfd;
    }

    .table-head h2 {
      margin: 0;
      font-size: 18px;
    }

    .result-meta {
      color: #52616f;
      font-size: 14px;
      font-weight: 700;
    }

    .table-scroll {
      overflow: auto;
      max-height: calc(100vh - 258px);
    }

    table {
      width: 100%;
      min-width: 1180px;
      border-collapse: collapse;
      table-layout: fixed;
    }

    th,
    td {
      padding: 12px 10px;
      border-bottom: 1px solid #e7edf2;
      text-align: left;
      vertical-align: top;
      font-size: 14px;
      word-break: keep-all;
    }

    th {
      position: sticky;
      top: 0;
      z-index: 1;
      background: #eef3f7;
      color: #354553;
      font-weight: 700;
    }

    tbody tr:hover {
      background: #f5fbfa;
    }

    .num {
      text-align: center;
      color: #607080;
    }

    .title-link {
      color: #155a9c;
      text-decoration: none;
      font-weight: 700;
      line-height: 1.45;
    }

    .title-link:hover {
      text-decoration: underline;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 3px 8px;
      border-radius: 4px;
      background: #eaf6f3;
      color: #1d6f66;
      font-weight: 700;
      white-space: nowrap;
    }

    .empty {
      padding: 34px;
      color: #607080;
      text-align: center;
      font-weight: 700;
    }

    @media (max-width: 1100px) {
      .filters {
        grid-template-columns: repeat(3, minmax(140px, 1fr));
      }
    }

    @media (max-width: 760px) {
      .top-bar {
        grid-template-columns: 1fr;
        padding: 18px;
      }

      .filters {
        grid-template-columns: 1fr;
      }

      .filter-field.wide {
        grid-column: auto;
      }

      .table-head {
        align-items: flex-start;
        flex-direction: column;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <header class="top-bar">
      <div>
        <h1>기업마당 지원사업 공고 크롤링</h1>
        <div class="source">
          <span>수집 범위: 1페이지 ~ 20페이지</span>
          <span>생성일시: __GENERATED_AT__</span>
          <a href="https://www.bizinfo.go.kr/sii/siia/selectSIIA200View.do?rows=15&cpage=1" target="_blank" rel="noopener">원본 사이트 열기</a>
        </div>
      </div>
      <div class="summary-box">
        <span>전체 공고</span>
        <strong id="totalCount">0</strong>
      </div>
    </header>

    <main class="content">
      <section class="filters" aria-label="지원사업 공고 필터">
        <div class="filter-field wide">
          <label for="keyword">지원사업명 검색</label>
          <input id="keyword" type="search" placeholder="공고명, 부처, 기관 검색">
        </div>
        <div class="filter-field">
          <label for="fieldFilter">지원분야</label>
          <select id="fieldFilter"></select>
        </div>
        <div class="filter-field">
          <label for="periodFrom">신청기간(from)</label>
          <input id="periodFrom" type="date">
        </div>
        <div class="filter-field">
          <label for="periodTo">신청기간(to)</label>
          <input id="periodTo" type="date">
        </div>
        <div class="filter-field">
          <label for="registeredAt">등록일</label>
          <input id="registeredAt" type="date">
        </div>
        <div class="filter-field wide">
          <label for="ministryFilter">소관부처·지자체</label>
          <select id="ministryFilter"></select>
        </div>
        <div class="filter-field wide">
          <label for="agencyFilter">사업수행기관</label>
          <select id="agencyFilter"></select>
        </div>
        <div class="filter-field">
          <label>&nbsp;</label>
          <button id="resetButton" type="button" class="secondary">필터 초기화</button>
        </div>
      </section>

      <section class="table-panel">
        <div class="table-head">
          <h2>지원사업 공고 목록</h2>
          <div class="result-meta" id="resultMeta">0건 표시 중</div>
        </div>
        <div class="table-scroll">
          <table>
            <colgroup>
              <col style="width: 70px">
              <col style="width: 95px">
              <col style="width: 360px">
              <col style="width: 150px">
              <col style="width: 150px">
              <col style="width: 190px">
              <col style="width: 120px">
              <col style="width: 85px">
              <col style="width: 70px">
            </colgroup>
            <thead>
              <tr>
                <th>번호</th>
                <th>지원분야</th>
                <th>지원사업명</th>
                <th>신청기간</th>
                <th>소관부처·지자체</th>
                <th>사업수행기관</th>
                <th>등록일</th>
                <th>조회수</th>
                <th>페이지</th>
              </tr>
            </thead>
            <tbody id="noticeRows"></tbody>
          </table>
          <div id="emptyState" class="empty" hidden>조건에 맞는 공고가 없습니다.</div>
        </div>
      </section>
    </main>
  </div>

  <script>
    const notices = __DATA_JSON__;
    const fields = __FIELDS_JSON__;
    const ministries = __MINISTRIES_JSON__;
    const agencies = __AGENCIES_JSON__;

    const controls = {
      keyword: document.getElementById("keyword"),
      field: document.getElementById("fieldFilter"),
      periodFrom: document.getElementById("periodFrom"),
      periodTo: document.getElementById("periodTo"),
      ministry: document.getElementById("ministryFilter"),
      agency: document.getElementById("agencyFilter"),
      registeredAt: document.getElementById("registeredAt"),
    };

    const rows = document.getElementById("noticeRows");
    const emptyState = document.getElementById("emptyState");
    const resultMeta = document.getElementById("resultMeta");
    const totalCount = document.getElementById("totalCount");
    const resetButton = document.getElementById("resetButton");

    function fillOptions(select, values, label) {
      select.innerHTML = `<option value="">전체 ${label}</option>` +
        values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function periodMatches(item, from, to) {
      if (!from && !to) {
        return true;
      }
      const itemFrom = item.periodFrom || "";
      const itemTo = item.periodTo || item.periodFrom || "";
      if (!itemFrom && !itemTo) {
        return false;
      }
      if (from && itemTo && itemTo < from) {
        return false;
      }
      if (to && itemFrom && itemFrom > to) {
        return false;
      }
      return true;
    }

    function applyFilters() {
      const keyword = controls.keyword.value.trim().toLowerCase();
      const field = controls.field.value;
      const from = controls.periodFrom.value;
      const to = controls.periodTo.value;
      const ministry = controls.ministry.value;
      const agency = controls.agency.value;
      const registeredAt = controls.registeredAt.value;

      const filtered = notices.filter((item) => {
        const keywordTarget = `${item.title} ${item.field} ${item.ministry} ${item.agency}`.toLowerCase();
        return (!keyword || keywordTarget.includes(keyword)) &&
          (!field || item.field === field) &&
          periodMatches(item, from, to) &&
          (!ministry || item.ministry === ministry) &&
          (!agency || item.agency === agency) &&
          (!registeredAt || item.registeredAt === registeredAt);
      });

      renderRows(filtered);
    }

    function renderRows(items) {
      rows.innerHTML = items.map((item) => `
        <tr>
          <td class="num">${escapeHtml(item.no)}</td>
          <td><span class="badge">${escapeHtml(item.field)}</span></td>
          <td><a class="title-link" href="${escapeHtml(item.url)}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a></td>
          <td>${escapeHtml(item.period)}</td>
          <td>${escapeHtml(item.ministry)}</td>
          <td>${escapeHtml(item.agency)}</td>
          <td>${escapeHtml(item.registeredAt)}</td>
          <td class="num">${escapeHtml(item.views)}</td>
          <td class="num">${escapeHtml(item.page)}</td>
        </tr>
      `).join("");

      emptyState.hidden = items.length > 0;
      resultMeta.textContent = `${items.length.toLocaleString()}건 표시 중`;
    }

    function resetFilters() {
      Object.values(controls).forEach((control) => {
        control.value = "";
      });
      applyFilters();
    }

    fillOptions(controls.field, fields, "지원분야");
    fillOptions(controls.ministry, ministries, "소관부처·지자체");
    fillOptions(controls.agency, agencies, "사업수행기관");
    totalCount.textContent = notices.length.toLocaleString();

    Object.values(controls).forEach((control) => {
      control.addEventListener("input", applyFilters);
      control.addEventListener("change", applyFilters);
    });
    resetButton.addEventListener("click", resetFilters);
    applyFilters();
  </script>
</body>
</html>
"""

    replacements = {
        "__GENERATED_AT__": escape(generated_at),
        "__DATA_JSON__": data_json,
        "__FIELDS_JSON__": fields_json,
        "__MINISTRIES_JSON__": ministries_json,
        "__AGENCIES_JSON__": agencies_json,
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def main():
    items = collect_items()
    OUTPUT_FILE.write_text(build_html(items), encoding="utf-8")
    print(f"{len(items)}건 저장 완료: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
