<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:atom="http://www.w3.org/2005/Atom">
  <xsl:output method="html" encoding="utf-8" indent="yes"/>

  <xsl:template match="/rss/channel">
    <html lang="en">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title><xsl:value-of select="title"/> (RSS feed)</title>
        <style>
          @font-face { font-family: "Oswald"; src: url("/fonts/oswald-var.woff2") format("woff2"); font-weight: 200 700; }
          @font-face { font-family: "Lato"; src: url("/fonts/lato-regular.woff2") format("woff2"); font-weight: 400; }
          @font-face { font-family: "Lato"; src: url("/fonts/lato-bold.woff2") format("woff2"); font-weight: 700; }
          * { box-sizing: border-box; }
          body { margin: 0; font-family: "Lato", -apple-system, "Segoe UI", sans-serif; color: #111214; background: #F5F6F8; line-height: 1.6; }
          header { background: #111214; color: #fff; padding: 48px 24px 40px; }
          .wrap { max-width: 760px; margin: 0 auto; }
          .dots span { display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 50%; margin-right: 8px; font-family: "Menlo", "SF Mono", ui-monospace, monospace; font-weight: 700; font-size: 20px; line-height: 1; }
          .n { background: #F4CE47; color: #111214; } .y { background: #111214; color: #fff; box-shadow: 0 0 0 2px rgba(255,255,255,.85); } .c { background: #314FA6; color: #fff; }
          h1 { font-family: "Oswald", "Arial Narrow", sans-serif; text-transform: uppercase; letter-spacing: .01em; font-size: 2.4rem; margin: 18px 0 8px; }
          header p { margin: 0; color: rgba(255,255,255,.78); }
          .notice { background: #fff; border: 1px solid rgba(17,18,20,.12); border-left: 4px solid #F4CE47; border-radius: 8px; padding: 16px 20px; margin: 28px 0; }
          .notice code { background: #F5F6F8; padding: 2px 6px; border-radius: 4px; word-break: break-all; }
          .notice a { color: #314FA6; font-weight: 700; }
          .card { background: #fff; border: 1px solid rgba(17,18,20,.12); border-radius: 14px; padding: 20px 24px; margin-bottom: 16px; }
          .card h2 { font-family: "Oswald", "Arial Narrow", sans-serif; text-transform: uppercase; font-size: 1.3rem; margin: 0 0 4px; line-height: 1.15; }
          .card h2 a { color: inherit; text-decoration: none; }
          .card h2 a:hover { color: #314FA6; }
          .date { color: #5A5F66; font-size: .95rem; }
          .btn { display: inline-block; margin-top: 12px; font-family: "Oswald", "Arial Narrow", sans-serif; text-transform: uppercase; letter-spacing: .08em; font-size: .85rem; font-weight: 600; background: #F4CE47; color: #111214; padding: 9px 18px; border-radius: 8px; text-decoration: none; }
          footer { text-align: center; color: #5A5F66; font-size: .9rem; padding: 12px 24px 48px; }
          footer a { color: #314FA6; }
        </style>
      </head>
      <body>
        <header>
          <div class="wrap">
            <div class="dots"><span class="n">N</span><span class="y">Y</span><span class="c">C</span></div>
            <h1><xsl:value-of select="title"/></h1>
            <p><xsl:value-of select="description"/></p>
          </div>
        </header>
        <div class="wrap">
          <div class="notice">
            <strong>This is an RSS feed.</strong> Copy this page's URL into your feed reader
            (or a Slack channel with <code>/feed subscribe</code>) to get new meetups as they're announced:
            <br/><code><xsl:value-of select="atom:link/@href"/></code>
            <br/><a href="{link}">&#8592; Back to nycmacadmins.com</a>
          </div>
          <xsl:for-each select="item">
            <div class="card">
              <h2><a href="{link}"><xsl:value-of select="title"/></a></h2>
              <xsl:variable name="h" select="number(substring(pubDate, 18, 2))"/>
              <xsl:variable name="h12" select="($h + 11) mod 12 + 1"/>
              <div class="date"><xsl:value-of select="substring(pubDate, 1, 16)"/> &#183; <xsl:value-of select="$h12"/>:<xsl:value-of select="substring(pubDate, 21, 2)"/><xsl:text> </xsl:text><xsl:choose><xsl:when test="$h &gt;= 12">PM</xsl:when><xsl:otherwise>AM</xsl:otherwise></xsl:choose></div>
              <a class="btn" href="{link}">Event details</a>
            </div>
          </xsl:for-each>
        </div>
        <footer>NYC Mac Admins &#183; <a href="{link}">nycmacadmins.com</a></footer>
      </body>
    </html>
  </xsl:template>

  <xsl:template match="/">
    <xsl:apply-templates select="rss/channel"/>
  </xsl:template>
</xsl:stylesheet>
