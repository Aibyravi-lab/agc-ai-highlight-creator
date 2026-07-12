// AGC-084: pure disablement decisions for UploadPanel, extracted out of
// the component so this JSX-free module is directly testable with
// node:test (this project has no jsdom/React-testing-library to render
// the component itself).

export interface UploadAvailability {
  maintenanceMode: boolean;
  outOfCredits: boolean;
}

export function isUploadInteractionDisabled({
  maintenanceMode,
  outOfCredits,
}: UploadAvailability): boolean {
  return maintenanceMode || outOfCredits;
}

export interface GenerateAvailability extends UploadAvailability {
  loading: boolean;
  hasSelectedFile: boolean;
  subscriptionLoading: boolean;
}

export function isGenerateDisabled({
  loading,
  hasSelectedFile,
  subscriptionLoading,
  ...availability
}: GenerateAvailability): boolean {
  return (
    loading ||
    !hasSelectedFile ||
    isUploadInteractionDisabled(availability) ||
    subscriptionLoading
  );
}
