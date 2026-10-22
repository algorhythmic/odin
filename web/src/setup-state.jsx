import { useEffect, useState } from 'preact/hooks';
import fixture from '../fixtures/setup.json';
import { createSetupStore } from './setup.js';

export const setupStore = createSetupStore(fixture, { fresh: new URLSearchParams(location.search).get('setup') === 'fresh' });
export function useSetup() {
  const [, setVersion] = useState(setupStore.getState().version);
  useEffect(() => setupStore.subscribe(setVersion), []);
  return setupStore.getState();
}
