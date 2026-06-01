# 크롤링 수행(HTTP 요청, HTML 파싱, 노이즈 제거, 문장 분리)

from playwright.async_api import Frame, Page, TimeoutError as PlaywrightTimeoutError, async_playwright
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass

import asyncio
import logging
import sys, os
import json
import re
import kss

MAX_PER_RATING = 30         # 별점별 목표 수집 개수
MIN_REVIEW_LENGTH = 20      # 최소 리뷰 길이
MAX_SCROLL_PER_RATING = 5   # 더보기 버튼 클릭 횟수

# 텍스트 인코딩 형식 강제 지정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

NOISE_LINE_PATTERNS = [
    r"^\d+\s*[.)]\s*$",
    r"^\d+\s*[.)]\s*[가-힣A-Za-z ]{1,12}$",
    r"^[-•·]\s*[가-힣A-Za-z ]{1,20}$",
    r"^(가격|배송|제품|기타)$",
    r".*구매\s*추천.*",
    r".*많이\s*파세요.*",
    r".*착한\s*가격.*유지.*",
]
NOISE_MARKERS = ["선택 옵션", "모델확인", "옵션 확인", "option", "model"]


@dataclass
class ReviewItem:
    rating: int
    text: str


# 리뷰 노이즈 제거 및 텍스트 정규화
def normalize_review_text(text: str) -> str:
    text = re.sub(r"&nbsp;?|&#160;?", " ", text, flags=re.IGNORECASE)
    text = text.replace("\u00a0", " ").replace("？", " ")
    lines = [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]
    kept_lines = [l for l in lines if not any(re.match(p, l, re.IGNORECASE) for p in NOISE_LINE_PATTERNS)]
    cleaned = " ".join(" ".join(kept_lines or lines).split())
    cleaned = re.sub(r"([!?.,~])\1{2,}", r"\1\1", cleaned)
    return re.sub(r"(ㅋ|ㅎ|ㅠ|ㅜ)\1{3,}", r"\1\1", cleaned).strip()


# 리뷰 품질 필터 (반복성/노이즈/한글 여부 통합 판별)
def is_valid_review(text: str) -> bool:
    if not text or len(text) < MIN_REVIEW_LENGTH:
        return False
    if not re.search(r"[가-힣ㄱ-ㅎㅏ-ㅣ]", text):
        return False
    if any(m in text.lower() for m in NOISE_MARKERS):
        return False
    chars = set(text) - {' '}
    if chars and max(text.count(ch) for ch in chars) / len(text) >= 0.55:
        return False
    if re.search(r"(.{2,5})\1{4,}", text):
        return False
    return True


# 리뷰 섹션으로 이동
async def goto_reviews_section(page: Page, product_url: str, logger: logging.Logger) -> None:
    await page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(1500)

    review_tab_selectors = [
        "a:has-text('리뷰')",
        "button:has-text('리뷰')",
        "[role='tab']:has-text('리뷰')",
        "a:has-text('상품평')",
        "button:has-text('상품평')",
    ]
    for selector in review_tab_selectors:
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                await locator.click(timeout=5000)
                logger.info("리뷰 탭 진입 성공: %s", selector)
                await page.wait_for_timeout(1200)
                return
        except Exception:
            continue

    logger.info("리뷰 탭 클릭 없이 현재 화면에서 리뷰 영역 탐색을 진행합니다.")


# 리뷰 컨텐츠가 담긴 프레임을 탐색
async def get_review_frame(page: Page, logger: logging.Logger) -> Optional[Frame]:
    for _ in range(20):
        for frame in page.frames:
            if "review-frame" in frame.url:
                logger.info("리뷰 iframe 발견: %s", frame.url)
                return frame
        await page.wait_for_timeout(500)
    return None


# 리뷰 프레임의 dom을 파싱하여 ReviewItem 리스트를 반환
async def extract_reviews_from_dom(frame: Frame) -> List[ReviewItem]:
    raw_reviews = await frame.evaluate(
        """
        () => {
          // 더보기 시 area_list가 교체/추가되는 케이스를 고려해
          // 최신 리스트(마지막) 우선으로 리뷰 블록을 수집한다.
          const areaLists = Array.from(document.querySelectorAll('ul.area_list'));
          const listOrder = areaLists.length > 0 ? areaLists.slice().reverse() : [];
          const latestList = listOrder.length > 0 ? listOrder[0] : document;
          const blocks = Array.from(latestList.querySelectorAll('li.review_list_element'));

          const results = [];

          for (const el of blocks) {
            const ratingText = (el.querySelector('p.grade em')?.textContent || '').trim();
            const rating = Number.parseInt(ratingText, 10);
            if (!rating || rating < 1 || rating > 5) continue;

            // 11번가 리뷰 본문은 상태/템플릿에 따라 클래스가 달라져서 다중 셀렉터로 안전 추출
            const bodySelectors = [
              'p.cont_review_hide.text-expanded',
              'p.cont_review_hide',
              'p.cont_review',
              'div.cont_review',
              'div.review_cont',
              '[class*="review"][class*="cont"] p',
            ];
            let body = '';
            for (const selector of bodySelectors) {
              const bodyEl = el.querySelector(selector);
              if (!bodyEl) continue;

              // <br>를 공백으로 변환한 뒤 텍스트 추출
              const clone = bodyEl.cloneNode(true);
              clone.querySelectorAll('br').forEach(br => br.replaceWith(' '));
              const text = (clone.textContent || '').replace(/\s+/g, ' ').trim();

              if (text) {
                body = text;
                break;
              }
            }

            results.push({
              rating,
              text: body,
              digest: `${rating}::${body.slice(0, 80)}`
            });
          }

          const dedup = new Map();
          for (const r of results) {
            if (!dedup.has(r.digest)) dedup.set(r.digest, r);
          }
          return Array.from(dedup.values());
        }
        """
    )
    return [
        ReviewItem(rating=int(r["rating"]), text=(r.get("text") or "").strip())
        for r in raw_reviews
        if 1 <= int(r.get("rating", 0)) <= 5
    ]


# dom 상태를 나타내는 시그니처 문자열을 생성
async def build_review_dom_signature(frame: Frame) -> str:
    return await frame.evaluate(
        """
        () => {
          const areaLists = Array.from(document.querySelectorAll('ul.area_list')).reverse();
          const latest = areaLists.length > 0 ? areaLists[0] : document;
          const blocks = Array.from(latest.querySelectorAll('li.review_list_element'));
          const sel = 'p.cont_review_hide.text-expanded, p.cont_review_hide, p.cont_review';
          const firstText = (blocks[0]?.querySelector(sel)?.textContent || '').trim();
          const lastText = (blocks[blocks.length - 1]?.querySelector(sel)?.textContent || '').trim();
          return `${areaLists.length}::${blocks.length}::${firstText.slice(0, 40)}::${lastText.slice(0, 40)}`;
        }
        """
    )

_WAIT_SIG_JS = """
    (prevSig) => {
      const areaLists = Array.from(document.querySelectorAll('ul.area_list')).reverse();
      const latest = areaLists.length > 0 ? areaLists[0] : document;
      const blocks = Array.from(latest.querySelectorAll('li.review_list_element'));
      const sel = 'p.cont_review_hide.text-expanded, p.cont_review_hide, p.cont_review';
      const firstText = (blocks[0]?.querySelector(sel)?.textContent || '').trim();
      const lastText = (blocks[blocks.length - 1]?.querySelector(sel)?.textContent || '').trim();
      return `${areaLists.length}::${blocks.length}::${firstText.slice(0, 40)}::${lastText.slice(0, 40)}` !== prevSig;
    }
"""


# 더보기 버튼을 클릭하고 dom이 갱신될때까지 대기
async def click_load_more_and_wait(frame: Frame, logger: logging.Logger, target_rating: int) -> bool:
    before_signature = await build_review_dom_signature(frame)
    clicked = await frame.evaluate(
        """
        () => {
          const btn = document.querySelector('div.area_btn.review-next-list-div button.review-next-list');
          if (!btn) return false;
          btn.click();
          return true;
        }
        """
    )
    if not clicked:
        logger.info("%s점에서 리뷰 더보기 버튼을 찾지 못해 중단합니다.", target_rating)
        return False

    logger.info("%s점: 리뷰 더보기 버튼 클릭 성공(JS click)", target_rating)
    try:
        await frame.wait_for_function(_WAIT_SIG_JS, before_signature, timeout=5000)
    except Exception:
        logger.info("%s점: 더보기 후 DOM 시그니처 변화가 없어 계속 진행합니다.", target_rating)
    await asyncio.sleep(0.6)
    return True


# 별점 필터 버튼 선택
async def select_rating_via_dropdown(frame: Frame, rating: int, logger: logging.Logger) -> bool:
    try:
        before_sig = await build_review_dom_signature(frame)
        selected = await frame.evaluate(
            """
            (score) => {
              const input = document.querySelector(`#star-score input[name='grade'][value='${score}']`);
              if (!input) return false;
              input.click();
              input.checked = true;
              input.dispatchEvent(new Event('input', { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));
              const form = input.closest('form');
              if (form) form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
              return true;
            }
            """,
            str(rating),
        )
        if not selected:
            logger.warning("%s점 라디오를 찾지 못했습니다.", rating)
            return False

        try:
            await frame.wait_for_function(_WAIT_SIG_JS, before_sig, timeout=5000)
        except Exception:
            logger.warning("%s점 필터 전환 후 DOM 변화 미감지, 그대로 진행합니다.", rating)

        await asyncio.sleep(0.5)
        logger.info("%s점 필터 선택 완료", rating)
        return True
    except Exception as exc:
        logger.warning("%s점 필터 선택 실패: %s", rating, exc)
        return False


# 별점별 리뷰 데이터 수집
async def collect_reviews(frame: Frame, logger: logging.Logger) -> Dict[int, List[ReviewItem]]:
    bucket: Dict[int, List[ReviewItem]] = {i: [] for i in range(1, 6)}
    seen: Set[str] = set()

    for target_rating in range(5, 0, -1):
        if not await select_rating_via_dropdown(frame, target_rating, logger):
            continue

        stagnant_count = 0
        # 최초 1회 수집 + 리뷰 더보기 최대 5회
        for load_step in range(MAX_SCROLL_PER_RATING + 1):
            before_bucket_len = len(bucket[target_rating])
            for review in await extract_reviews_from_dom(frame):
                if review.rating != target_rating:
                    continue
                text = normalize_review_text(review.text)
                key = f"{target_rating}::{text[:160]}"
                if key in seen or len(bucket[target_rating]) >= MAX_PER_RATING or not is_valid_review(text):
                    continue
                seen.add(key)
                bucket[target_rating].append(ReviewItem(rating=target_rating, text=text))

            added_count = len(bucket[target_rating]) - before_bucket_len
            stagnant_count = 0 if added_count else stagnant_count + 1

            if len(bucket[target_rating]) >= MAX_PER_RATING:
                break

            # 연속 정체 2회면 중단
            if stagnant_count >= 2:
                logger.info("%s점에서 추가 로딩 후 신규 리뷰 누적이 없어 중단합니다.", target_rating)
                break

            # 더보기 최대 횟수 도달 시 종료
            if load_step >= MAX_SCROLL_PER_RATING:
                break

            if not await click_load_more_and_wait(frame, logger, target_rating):
                break

        logger.info("수집 진행(rating=%s): %s", target_rating, {r: len(v) for r, v in bucket.items()})

    return bucket


# 평균 별점 추출
async def extract_average_review_rate(page: Page, frame: Frame, logger: logging.Logger) -> Optional[str]:
    JS = "() => (document.querySelector('div.c_product_review_rate1 em')?.textContent || '').trim()"
    for ctx, name in [(frame, "frame"), (page, "page")]:
        try:
            value = await ctx.evaluate(JS)
            match = re.search(r"([0-5](?:\.\d)?)", value or "")
            if match:
                logger.info("평균 평점 추출 성공(%s): %s", name, match.group(1))
                return match.group(1)
        except Exception:
            pass
    logger.warning("평균 평점(c_product_review_rate1 em)을 찾지 못했습니다.")
    return None


# 메인 함수
async def fetch_reviews(url: str) -> Dict[str, Any]:
    logger = logging.getLogger("logger")

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=False)
            page = await browser.new_page()

            await goto_reviews_section(page, url, logger)
            frame = await get_review_frame(page, logger)
            if frame is None:
                raise RuntimeError("리뷰 iframe(review-frame)을 찾지 못했습니다.")

            average_review_rate = await extract_average_review_rate(page, frame, logger)
            bucket = await collect_reviews(frame, logger)
            await browser.close()

        missing = [r for r, items in bucket.items() if len(items) < MAX_PER_RATING]
        if missing:
            logger.warning("일부 평점은 목표 개수(%s개)를 채우지 못했습니다: %s", MAX_PER_RATING, missing)
        else:
            logger.info("모든 평점(1~5점)에서 %s개씩 수집을 완료했습니다.", MAX_PER_RATING)

        output = {
            "average_review_rate": average_review_rate,
            "reviews_by_rating": {
                rating: [item.text for item in items]
                for rating, items in sorted(bucket.items(), reverse=True)
            },
        }
        
        result = []

        for key in output["reviews_by_rating"].keys():
            for content in output["reviews_by_rating"][key]:
                sentences = kss.split_sentences(content, backend="mecab")

                for sentence in sentences:
                    result.append(sentence)
         
        return {
            "average_review_rate": output["average_review_rate"],
            "sentences": result,
        }

    except PlaywrightTimeoutError as exc:
        logger.exception("페이지 로딩/클릭 타임아웃 발생: %s", exc)
        raise
    except Exception as exc:
        logger.exception("예상치 못한 오류 발생: %s", exc)
        raise