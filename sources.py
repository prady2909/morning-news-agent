"""
sources.py — Master list of RSS feeds for the morning news aggregator.

Each entry is a dict with four required keys:
  name  : human-readable label, used in reports and (later) email subjects
  topic : one of PM | GTM | AI | Startups
  type  : "article" (blog/newsletter) or "video" (YouTube channel)
  url   : the RSS/Atom feed URL

Optional key:
  max_items : per-feed cap on how many items land on the page. Omit it to use
              build_page.py's default (MAX_ITEMS_PER_FEED). The YouTube feeds set
              this low so their frequent uploads don't bury the PM/GTM/Startups feeds.

Lines marked  # VERIFY  mean I couldn't confirm the exact feed URL from
memory — the guess is reasonable but test it and replace if it's dead.

YouTube RSS format:
  https://www.youtube.com/feeds/videos.xml?channel_id=<CHANNEL_ID>
To find a channel's ID: open the channel page → right-click → View Page
Source → Ctrl+F for "channelId". Paste the 24-char UC… string below.
"""

FEEDS = [

    # ── PM ────────────────────────────────────────────────────────────────

    {
        "name": "Lenny's Newsletter",
        "topic": "PM",
        "type": "article",
        "url": "https://www.lennysnewsletter.com/feed",
        # Substack with custom domain — feed URL is reliable
    },
    {
        "name": "Marty Cagan (SVPG)",
        "topic": "PM",
        "type": "article",
        "url": "https://svpg.com/feed/",  # VERIFY — SVPG is WordPress; /feed/ is the standard WP path
    },
    {
        "name": "Julie Zhuo (The Looking Glass)",
        "topic": "PM",
        "type": "article",
        "url": "https://lg.substack.com/feed",  # VERIFY — may be juliezhuo.substack.com instead
    },
    {
        "name": "Aakash Gupta (Product Growth)",
        "topic": "PM",
        "type": "article",
        "url": "https://aakashg.substack.com/feed",  # VERIFY
    },
    {
        "name": "Melissa Perri",
        "topic": "PM",
        "type": "article",
        "url": "https://melissaperri.substack.com/feed",  # VERIFY — also check productcraft.com/rss
    },
    {
        "name": "The Beautiful Mess",
        "topic": "PM",
        "type": "article",
        "url": "https://cutlefish.substack.com/feed",
    },
    {
        "name": "Itamar Gilad",
        "topic": "PM",
        "type": "article",
        "url": "https://itamargilad.com/feed",
    },

    # ── GTM ───────────────────────────────────────────────────────────────

    # DEAD — Kyle Poyar (Growth Unhinged): every URL variant (custom domain + substack
    # subdomain) returned malformed XML or 404 when tested 2026-07-03.
    # Try again at: https://www.growthunhinged.com/feed or growthunhinged.substack.com/feed
    # {
    #     "name": "Kyle Poyar (Growth Unhinged)",
    #     "topic": "GTM",
    #     "type": "article",
    #     "url": "https://www.growthunhinged.com/feed",
    # },
    {
        "name": "Maja Voje (GTM Strategist)",
        "topic": "GTM",
        "type": "article",
        "url": "https://gtmstrategist.substack.com/feed",  # VERIFY
    },
    {
        "name": "Sean Ellis",
        "topic": "GTM",
        "type": "article",
        "url": "https://seanellis.substack.com/feed",  # hackinggrowth.com/rss is dead; Substack confirmed working
    },
    {
        "name": "The GTM Engineer (Clay)",
        "topic": "GTM",
        "type": "article",
        "url": "https://thegtmengineer.substack.com/feed",  # VERIFY — Clay's GTM-focused newsletter
    },
    {
        "name": "Stuart Balcombe (ConnectedGTM)",
        "topic": "GTM",
        "type": "article",
        "url": "https://stuartbalcombe.substack.com/feed",  # VERIFY
    },
    # DEAD — Alex Lindahl (GTM Foundry): alexlindahl.substack.com returns HTML (no public feed),
    # gtmfoundry.substack.com doesn't exist. Needs correct platform/URL.
    # {
    #     "name": "Alex Lindahl (GTM Foundry)",
    #     "topic": "GTM",
    #     "type": "article",
    #     "url": "https://alexlindahl.substack.com/feed",
    # },
    {
        "name": "April Dunford",
        "topic": "GTM",
        "type": "article",
        "url": "https://aprildunford.substack.com/feed",
    },
    {
        "name": "MKT1",
        "topic": "GTM",
        "type": "article",
        "url": "https://newsletter.mkt1.co/feed",
    },
    {
        "name": "GTMnow",
        "topic": "GTM",
        "type": "article",
        "url": "https://thegtmnewsletter.substack.com/feed",
    },

    # ── AI ────────────────────────────────────────────────────────────────

    # DEAD — Andrew Ng (The Batch): all deeplearning.ai feed paths return 404 or malformed XML
    # when tested 2026-07-03. The Batch may have moved to a newsletter platform with no RSS.
    # {
    #     "name": "Andrew Ng (The Batch)",
    #     "topic": "AI",
    #     "type": "article",
    #     "url": "https://www.deeplearning.ai/the-batch/feed/",
    # },

    # DEAD — Jeremy Howard (fast.ai): /atom.xml, /rss.xml, /feed.xml all return 404.
    # The fast.ai blog may have migrated; check fast.ai for a current feed link.
    # {
    #     "name": "Jeremy Howard (fast.ai)",
    #     "topic": "AI",
    #     "type": "article",
    #     "url": "https://www.fast.ai/atom.xml",
    # },

    {
        "name": "Import AI",
        "topic": "AI",
        "type": "article",
        "url": "https://importai.substack.com/feed",
    },
    {
        "name": "Ahead of AI",
        "topic": "AI",
        "type": "article",
        "url": "https://magazine.sebastianraschka.com/feed",
    },
    {
        "name": "Interconnects",
        "topic": "AI",
        "type": "article",
        "url": "https://www.interconnects.ai/feed",
    },

    # ── Startups ──────────────────────────────────────────────────────────

    {
        "name": "Y Combinator Blog",
        "topic": "Startups",
        "type": "article",
        "url": "https://www.ycombinator.com/blog/rss.xml",  # VERIFY — try /feed or /rss if this 404s
    },
    # DEAD — First Round Review: /rss, /feed, /rss.xml all return malformed XML or 404.
    # First Round may no longer publish an RSS feed; check review.firstround.com for a feed link.
    # {
    #     "name": "First Round Review",
    #     "topic": "Startups",
    #     "type": "article",
    #     "url": "https://review.firstround.com/rss",
    # },
    {
        "name": "Elad Gil",
        "topic": "Startups",
        "type": "article",
        "url": "https://blog.eladgil.com/feed",
    },
    {
        "name": "Not Boring",
        "topic": "Startups",
        "type": "article",
        "url": "https://www.notboring.co/feed",
    },
    {
        "name": "Newcomer",
        "topic": "Startups",
        "type": "article",
        "url": "https://newcomer.co/feed",
    },
    {
        "name": "SaaStr",
        "topic": "Startups",
        "type": "article",
        "url": "https://saastr.com/feed",
        "max_items": 8,  # high-volume — cap so one source can't dominate the page
    },

    # ── YouTube Channels ──────────────────────────────────────────────────
    # All channel_ids below marked VERIFY — look them up from the channel page.
    # Placeholder format: UC + 22 x's means "not yet filled in".

    {
        "name": "Claire Vo (ChatPRD)",
        "topic": "PM",
        "type": "video",
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCRYY7IEbkHLH_ScJCu9eWDQ",
        "max_items": 4,
    },
    {
        "name": "Andrej Karpathy",
        "topic": "AI",
        "type": "video",
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCYO_jab_esuFRV4b17AJtAw",
        "max_items": 4,
    },
    {
        "name": "Matt Wolfe",
        "topic": "AI",
        "type": "video",
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UChpleBmo18P08aKCIgti38g",
        "max_items": 4,
    },
    {
        "name": "AI Explained",
        "topic": "AI",
        "type": "video",
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCNJ1Ymd5yFuUPtn21xtRbbw",
        "max_items": 4,
    },
    {
        "name": "Corbin Brown",
        "topic": "AI",
        "type": "video",
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCJFMlSxcvlZg5yZUYJT0Pug",
        "max_items": 4,
    },
    {
        "name": "The AI Automators",
        "topic": "AI",
        "type": "video",
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCwvXnrOCRlhokHlJwohf2OA",
        "max_items": 4,
    },
    {
        "name": "Alex Finn",
        "topic": "AI",
        "type": "video",
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCfQNB91qRP_5ILeu_S_bSkg",
        "max_items": 4,
    },
    {
        "name": "Y Combinator (YouTube)",
        "topic": "Startups",
        "type": "video",
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCcefcZRL2oaA_uBNeo5UOWg",  # VERIFY — most-cited ID for YC's channel
        "max_items": 4,
    },
]
