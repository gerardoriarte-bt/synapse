import React from 'react';

interface Props {
  responseId: string;
  data?: unknown[];
}

export const ActionToolbar: React.FC<Props> = ({ responseId, data }) => {
  void responseId;
  void data;
  return null;
};
