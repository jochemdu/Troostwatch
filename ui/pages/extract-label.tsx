import React from "react";
import Layout from "../components/Layout";
import LabelExtractor from "../components/LabelExtractor";
import ExampleLotEventConsumer from '../components/ExampleLotEventConsumer';

export default function ExtractLabelPage() {
  return (
    <>
      <Layout>
        <h1 style={{ marginTop: 32 }}>Extract Label from Image</h1>
        <LabelExtractor />
      </Layout>
      <ExampleLotEventConsumer />
    </>
  );
}
