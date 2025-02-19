import {
  render,
  screen,
  userEvent,
  waitForElementToBeRemoved,
} from 'sentry-test/reactTestingLibrary';

import GuideActions from 'sentry/actions/guideActions';
import GuideAnchor from 'sentry/components/assistant/guideAnchor';
import ConfigStore from 'sentry/stores/configStore';

describe('GuideAnchor', function () {
  const serverGuide = [
    {
      guide: 'issue',
      seen: false,
    },
  ];

  beforeEach(function () {
    ConfigStore.config = {
      user: {
        isSuperuser: false,
        dateJoined: new Date(2020, 0, 1),
      },
    };
  });

  it('renders, advances, and finishes', async function () {
    render(
      <div>
        <GuideAnchor target="issue_title" />
        <GuideAnchor target="exception" />
      </div>
    );

    GuideActions.fetchSucceeded(serverGuide);
    expect(await screen.findByText("Let's Get This Over With")).toBeInTheDocument();

    // XXX(epurkhiser): Skip pointer event checks due to a bug with how Popper
    // renders the hovercard with pointer-events: none. See [0]
    //
    // [0]: https://github.com/testing-library/user-event/issues/639
    //
    // NOTE(epurkhiser): We may be able to remove the skipPointerEventsCheck
    // when we're on popper >= 1.
    userEvent.click(screen.getByLabelText('Next'), undefined, {
      skipPointerEventsCheck: true,
    });

    expect(await screen.findByText('Narrow Down Suspects')).toBeInTheDocument();
    expect(screen.queryByText("Let's Get This Over With")).not.toBeInTheDocument();

    // Clicking on the button in the last step should finish the guide.
    const finishMock = MockApiClient.addMockResponse({
      method: 'PUT',
      url: '/assistant/',
    });

    userEvent.click(screen.getByLabelText('Enough Already'), undefined, {
      skipPointerEventsCheck: true,
    });

    expect(finishMock).toHaveBeenCalledWith(
      '/assistant/',
      expect.objectContaining({
        method: 'PUT',
        data: {
          guide: 'issue',
          status: 'viewed',
        },
      })
    );
  });

  it('dismisses', async function () {
    render(
      <div>
        <GuideAnchor target="issue_title" />
        <GuideAnchor target="exception" />
      </div>
    );

    GuideActions.fetchSucceeded(serverGuide);
    expect(await screen.findByText("Let's Get This Over With")).toBeInTheDocument();

    const dismissMock = MockApiClient.addMockResponse({
      method: 'PUT',
      url: '/assistant/',
    });

    userEvent.click(screen.getByLabelText('Dismiss'), undefined, {
      skipPointerEventsCheck: true,
    });

    expect(dismissMock).toHaveBeenCalledWith(
      '/assistant/',
      expect.objectContaining({
        method: 'PUT',
        data: {
          guide: 'issue',
          status: 'dismissed',
        },
      })
    );

    await waitForElementToBeRemoved(() => screen.queryByText("Let's Get This Over With"));
  });

  it('renders no container when inactive', function () {
    render(
      <GuideAnchor target="target 1">
        <span data-test-id="child-div" />
      </GuideAnchor>
    );

    expect(screen.queryByTestId('guide-container')).not.toBeInTheDocument();
    expect(screen.getByTestId('child-div')).toBeInTheDocument();
  });

  it('renders children when disabled', async function () {
    render(
      <GuideAnchor disabled target="exception">
        <div data-test-id="child-div" />
      </GuideAnchor>
    );

    expect(screen.queryByTestId('guide-container')).not.toBeInTheDocument();
    expect(screen.getByTestId('child-div')).toBeInTheDocument();
  });
});
