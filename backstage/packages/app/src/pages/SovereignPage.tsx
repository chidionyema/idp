import React from 'react';
import { Header, Page, Content } from '@backstage/core-components';
import SovereignViewer from '../components/sovereignViewer/SovereignViewer';

const SovereignPage: React.FC = () => {
  return (
    <Page themeId="tool">
      <Header title="Infrastructure Topology" subtitle="Sovereign: DAG + Drift Detection" />
      <Content>
        <SovereignViewer />
      </Content>
    </Page>
  );
};

export default SovereignPage;
