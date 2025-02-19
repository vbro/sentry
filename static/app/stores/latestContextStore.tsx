import {createStore, StoreDefinition} from 'reflux';

import OrganizationActions from 'sentry/actions/organizationActions';
import OrganizationsActions from 'sentry/actions/organizationsActions';
import ProjectActions from 'sentry/actions/projectActions';
import {Organization, Project} from 'sentry/types';
import {
  makeSafeRefluxStore,
  SafeRefluxStore,
  SafeStoreDefinition,
} from 'sentry/utils/makeSafeRefluxStore';

type OrgTypes = Organization | null;

type State = {
  environment: string | string[] | null;
  lastProject: Project | null;
  organization: OrgTypes;
  project: Project | null;
};

type LatestContextStoreInterface = {
  get(): State;
  onSetActiveOrganization(organization: OrgTypes): void;
  onSetActiveProject(project: Project | null): void;
  onUpdateOrganization(organization: OrgTypes): void;
  onUpdateProject(project: Project | null): void;
  reset(): void;
  state: State;
};

/**
 * Keeps track of last usable project/org this currently won't track when users
 * navigate out of a org/project completely, it tracks only if a user switches
 * into a new org/project.
 *
 * Only keep slug so that people don't get the idea to access org/project data
 * here Org/project data is currently in organizationsStore/projectsStore
 */
const storeConfig: StoreDefinition & LatestContextStoreInterface & SafeStoreDefinition = {
  unsubscribeListeners: [],

  state: {
    project: null,
    lastProject: null,
    organization: null,
    environment: null,
  },

  get() {
    return this.state;
  },

  init() {
    this.reset();

    this.unsubscribeListeners.push(
      this.listenTo(ProjectActions.setActive, this.onSetActiveProject)
    );
    this.unsubscribeListeners.push(
      this.listenTo(ProjectActions.updateSuccess, this.onUpdateProject)
    );
    this.unsubscribeListeners.push(
      this.listenTo(OrganizationsActions.setActive, this.onSetActiveOrganization)
    );
    this.unsubscribeListeners.push(
      this.listenTo(OrganizationsActions.update, this.onUpdateOrganization)
    );
    this.unsubscribeListeners.push(
      this.listenTo(OrganizationActions.update, this.onUpdateOrganization)
    );
  },

  reset() {
    this.state = {
      project: null,
      lastProject: null,
      organization: null,
      environment: null,
    };
    return this.state;
  },

  onUpdateOrganization(org) {
    // Don't do anything if base/target orgs are falsey
    if (!this.state.organization) {
      return;
    }
    if (!org) {
      return;
    }
    // Check to make sure current active org is what has been updated
    if (org.slug !== this.state.organization.slug) {
      return;
    }

    this.state = {
      ...this.state,
      organization: org,
    };
    this.trigger(this.state);
  },

  onSetActiveOrganization(org) {
    if (!org) {
      this.state = {
        ...this.state,
        organization: null,
        project: null,
      };
    } else if (!this.state.organization || this.state.organization.slug !== org.slug) {
      // Update only if different
      this.state = {
        ...this.state,
        organization: org,
        project: null,
      };
    }

    this.trigger(this.state);
  },

  onSetActiveProject(project) {
    if (!project) {
      this.state = {
        ...this.state,
        lastProject: this.state.project,
        project: null,
      };
    } else if (!this.state.project || this.state.project.slug !== project.slug) {
      // Update only if different
      this.state = {
        ...this.state,
        lastProject: this.state.project,
        project,
      };
    }

    this.trigger(this.state);
  },

  onUpdateProject(project) {
    this.state = {
      ...this.state,
      project,
    };
    this.trigger(this.state);
  },
};

const LatestContextStore = createStore(
  makeSafeRefluxStore(storeConfig)
) as SafeRefluxStore & LatestContextStoreInterface;

export default LatestContextStore;
