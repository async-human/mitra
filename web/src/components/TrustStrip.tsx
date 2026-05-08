/**
 * Backers / press messaging without empty logo placeholders.
 * Drop logo assets later by replacing this strip with imagery if needed.
 */

export function TrustStrip() {
  return (
    <section className="ts" aria-label="Company snapshot">
      <div className="ts-inner">
        <div className="ts-beta">
          <span className="ts-beta-dot" aria-hidden="true" />
          Private beta · India-wide coverage
        </div>

        <div className="ts-lines">
          <p className="ts-line">
            <span className="ts-line-label">Backed by</span>
            <span className="ts-line-body">
              venture funds backing India&apos;s internet and software economy.
            </span>
          </p>
          <p className="ts-line ts-line-muted">
            <span className="ts-line-label">As seen in</span>
            <span className="ts-line-names">
              YourStory · Inc42 · ET Tech · The Ken
            </span>
          </p>
        </div>
      </div>
    </section>
  );
}
