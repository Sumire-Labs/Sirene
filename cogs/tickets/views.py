import discord
from discord.ui import View, Button, button

class TicketCreateView(View):
    def __init__(self):
        # timeout=None makes the view persistent.
        # A custom_id is required for persistent views.
        super().__init__(timeout=None)

    @button(label="チケットを作成", style=discord.ButtonStyle.success, emoji="✉️", custom_id="ticket_create_button")
    async def create_ticket_callback(self, button: Button, interaction: discord.Interaction):
        """Callback for the create ticket button."""
        # The actual ticket creation logic is in the TicketCore cog.
        # We fetch the cog and call its method.
        # interaction.client refers to the Bot instance.
        ticket_cog = interaction.client.get_cog("TicketCore")
        if ticket_cog:
            await ticket_cog.create_ticket_channel(interaction)
        else:
            # This is a fallback error message if the cog isn't loaded for some reason.
            await interaction.response.send_message("チケット作成機能でエラーが発生しました。管理者に連絡してください。", ephemeral=True)
