from uuid import uuid4
import asyncio
import discord


class AwaitableView(discord.ui.View):
    def __init__(self, buttons_with_values, timeout):
        super().__init__(timeout=timeout)
        self._future = asyncio.Future()
        self._values_for_button_ids = dict()

        for button, value in buttons_with_values:
            button.custom_id = str(uuid4())
            self._values_for_button_ids[button.custom_id] = value
            self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # print("Button view interacted with: " + interaction.data["custom_id"])
        await interaction.response.defer()
        if not self._future.done():
            self._future.set_result(interaction.data["custom_id"])
        else:
            print("This view has already been resolved?  Shouldn't happen...")
        return True

    async def on_timeout(self):
        # print("Button view timed out!")
        await super().on_timeout()
        if not self._future.done():
            self._future.set_result(None)

    async def wait_for_value(self):
        # print("Button view waiting...")
        custom_id = await self._future
        # print("Button view got value: " + custom_id if custom_id else "None")
        return self._values_for_button_ids.get(custom_id)
