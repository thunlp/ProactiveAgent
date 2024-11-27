'''
This file set up the channels to let different components communicate with each other.
'''
from codelinker import ChannelTag,Channels

class AgentChannels(Channels):
    """Agent channel tags."""
    @property
    def propose(self):
        """Propose channel is used to store the proposal from the agent."""
        return ChannelTag(self.prefix + "propose")

    @property
    def operations(self):
        """Ops channel is used to store agent's available operations."""
        return ChannelTag(self.prefix + "operations")

    @property
    def execute(self):
        """The channel that triggers the agent execute the operation."""
        return ChannelTag(self.prefix + "execute")

class PCChannels(Channels):
    """PC channel tags."""
    
    @property
    def notify(self):
        """Notify channel is used trigger let the PC do the execution."""
        return ChannelTag(self.prefix + "notify")

    @property
    def feedback(self):
        """Feedback channel is used to inform the agent about the user's feedback"""
        return ChannelTag(self.prefix + "feedback")

class AndroidChannels(Channels):
    @property
    def write(self):
        """Write to the socket."""
        return ChannelTag(self.prefix + "write")

    @property
    def read(self):
        """Read from the socket."""
        return ChannelTag(self.prefix + "read")

class AllChannels(Channels):
    def __init__(self):
        super().__init__("")
        self.agent = AgentChannels("agent")
        self.pc = PCChannels("pc")
        self.android = AndroidChannels("android")

    @property
    def setup(self):
        """Setup channel is used to inform all components to setup."""
        return ChannelTag("setup")

    @property
    def activity(self):
        """Activity is used to mutually exclusive agent and the environment."""
        return ChannelTag("activity")

    @property
    def observation(self):
        """Observation channel is used to store the obsevation and trigger the agent to propose."""
        return ChannelTag("observation")

sc = AllChannels()

if __name__ == "__main__":
    print(sc.all)