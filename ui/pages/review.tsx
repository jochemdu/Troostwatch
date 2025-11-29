/**
 * Review Queue page for manually reviewing extracted product codes.
 *
 * This page allows operators to approve or reject codes that were
 * extracted from lot images but did not meet the auto-approve threshold.
 */
import { useState } from 'react';
import Layout from '../components/Layout';
import ReviewQueue from '../components/ReviewQueue';
import ExampleLotEventConsumer from '../components/ExampleLotEventConsumer';
import type { ReviewStatsResponse } from '../lib/generated';

export default function ReviewPage() {
  const [stats, setStats] = useState<ReviewStatsResponse | null>(null);

  return (
    <>
      <Layout>
        <div className="page-header">
          <h1>Code Review Queue</h1>
          <p className="subtitle">
            Review and approve extracted product codes from lot images.
            Codes with high confidence are auto-approved; lower confidence codes need manual review.
          </p>
        </div>

        <ReviewQueue onStatsUpdate={setStats} />

        <style jsx>{`
          .page-header {
            margin-bottom: 24px;
          }
          .page-header h1 {
            margin-bottom: 8px;
          }
          .subtitle {
            opacity: 0.7;
            max-width: 600px;
          }
        `}</style>
      </Layout>
      <ExampleLotEventConsumer />
    </>
  );
}
