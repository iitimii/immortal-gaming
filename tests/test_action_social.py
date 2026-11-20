
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.classes.mutual_action.conversation import Conversation
from src.classes.action_runtime import ActionStatus
from src.classes.event import Event
from src.server.runtime.session import DEFAULT_GAME_STATE, GameSessionRuntime

class TestActionSocial:
    
    @pytest.fixture
    def target_avatar(self, dummy_avatar):
        target = MagicMock()
        target.name = "FriendDummy"
        target.id = "friend_id"
        target.is_dead = False
        target.get_info.return_value = "Target Info"
        target.get_planned_actions_str.return_value = "None"
        target.thinking = ""
        # Mock add_event
        target.events = []
        target.add_event = lambda e, to_sidebar=False: target.events.append(e)
        # Mock cultivation progress (used for relation checks)
        target.cultivation_progress.level = 10
        target.gender = dummy_avatar.gender # same gender
        target.get_relation.return_value = None
        
        return target

    @pytest.mark.asyncio
    @patch("src.classes.mutual_action.mutual_action.call_llm_with_task_name", new_callable=AsyncMock)
    async def test_conversation_flow(self, mock_llm, dummy_avatar, target_avatar):
        """Test the conversation flow: Step -> LLM -> Feedback."""
        
        # 1. Prepare the mocked LLM response
        mock_response = {
            "FriendDummy": {
                "thinking": "He is nice.",
                "conversation_content": "Hello there!",
                "feedback": "Accept" # Conversation does not require feedback; content is what matters
            }
        }
        mock_llm.return_value = mock_response
        
        # Inject the World lookup
        dummy_avatar.world.avatar_manager.avatars = {target_avatar.name: target_avatar}
        
        # Mock our own level (so a mocked value in dummy_avatar does not break comparisons)
        dummy_avatar.cultivation_progress.level = 10

        # 2. Initialize the action
        action = Conversation(dummy_avatar, dummy_avatar.world)
        action._start_month_stamp = 100
        
        # 3. First step: should start the LLM task and return RUNNING
        res1 = action.step(target_avatar=target_avatar)
        assert res1.status == ActionStatus.RUNNING
        assert action._response_task is not None
        
        # Wait for the task to finish
        await action._response_task
        
        # 4. Second step: consume the result
        res2 = action.step(target_avatar=target_avatar)
        assert res2.status == ActionStatus.COMPLETED
        
        # 5. Verify the result
        # There should be an event containing the conversation content
        assert len(res2.events) >= 1
        content_event = res2.events[0]
        assert "Hello there!" in content_event.content
        assert dummy_avatar.id in content_event.related_avatars
        assert target_avatar.id in content_event.related_avatars
        
        # Verify the target's thinking was updated
        assert target_avatar.thinking == "He is nice."

    def test_conversation_no_target(self, dummy_avatar):
        action = Conversation(dummy_avatar, dummy_avatar.world)
        res = action.step(target_avatar=None)
        assert res.status == ActionStatus.FAILED

    @pytest.mark.asyncio
    async def test_conversation_uses_roleplay_session_when_avatar_controlled(self, dummy_avatar, target_avatar):
        runtime = GameSessionRuntime(dict(DEFAULT_GAME_STATE))
        dummy_avatar.world.runtime = runtime
        runtime.set_world_and_sim(dummy_avatar.world, None)
        runtime.get_roleplay_session()["controlled_avatar_id"] = dummy_avatar.id
        runtime.get_roleplay_session()["status"] = "observing"

        action = Conversation(dummy_avatar, dummy_avatar.world)
        action._start_month_stamp = 100

        res1 = action.step(target_avatar=target_avatar)
        assert res1.status == ActionStatus.RUNNING
        assert runtime.get_roleplay_session()["status"] == "conversing"
        assert runtime.get_roleplay_session()["pending_request"]["type"] == "conversation"

        runtime.get_roleplay_session()["status"] = "observing"
        runtime.get_roleplay_session()["pending_request"] = None
        runtime.get_roleplay_session()["conversation_session"]["status"] = "completed"
        runtime.get_roleplay_session()["conversation_session"]["last_summary"] = {
            "summary": "The two spoke briefly, sounding out each other's intentions.",
            "relation_hint": "",
            "story_hint": "",
        }
        runtime.get_roleplay_session()["conversation_session"]["last_ai_thinking"] = "Observe his intentions first."

        res2 = action.step(target_avatar=target_avatar)
        assert res2.status == ActionStatus.COMPLETED
        assert len(res2.events) == 1
        assert "sounding out each other's intentions" in res2.events[0].content
        assert target_avatar.thinking == "Observe his intentions first."

    @pytest.mark.asyncio
    async def test_conversation_finish_uses_relation_and_story_hints(self, dummy_avatar, target_avatar):
        action = Conversation(dummy_avatar, dummy_avatar.world)
        action._conversation_target = target_avatar
        action._conversation_result_text = "The conversation slowed and the mood was no longer as tense as before."
        action._conversation_relation_hint = "relations eased slightly"
        action._conversation_story_hint = "The conversation carried a sense of easing after the probing."

        with patch(
            "src.classes.mutual_action.conversation.RelationDeltaService.resolve_event_text_delta",
            new_callable=AsyncMock,
        ) as mock_resolve_delta, patch(
            "src.classes.mutual_action.conversation.RelationDeltaService.apply_bidirectional_delta"
        ) as mock_apply_delta, patch(
            "src.classes.mutual_action.conversation.StoryEventService.maybe_create_story",
            new_callable=AsyncMock,
        ) as mock_story:
            mock_resolve_delta.return_value = (1, 2)
            mock_story.return_value = None

            events = await action.finish(target_avatar=target_avatar)

        assert events == []
        assert mock_resolve_delta.await_count == 1
        assert "[relation_hint=relations eased slightly]" in mock_resolve_delta.await_args.kwargs["event_text"]
        assert mock_story.await_args.kwargs["prompt"] == "The conversation carried a sense of easing after the probing."
        mock_apply_delta.assert_called_once_with(dummy_avatar, target_avatar, 1, 2)
