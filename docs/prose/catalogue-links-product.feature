# crew#269: needs the cluster's Backstage; nothing runs this. Prose until a drill reads it.
Feature: A product's UIs enter the catalogue from the product's own repository
  Scenario: A product's UIs enter the catalogue from the product's own repository
    Given prospector carries catalog-info.yaml with a Component per HTTPRoute hostname in deploy/k8s/base/edge.yaml
    And backstage/app-config.container.yaml lists that file as a url location
    When the cluster's Backstage reconciles its locations
    Then prospector-store-web and prospector-store-api appear with links to mumchimp.com and api.mumchimp.com
    And a hostname the edge serves that the file does not name fails prospector's unit suite
