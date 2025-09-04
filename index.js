const { Client, GatewayIntentBits, EmbedBuilder } = require('discord.js');

// Hunt spot codes and names
const huntSpots = {
  '1x': 'Jaded Roots',
  '2x': 'Ancient Sewers', 
  '3x': 'Deeper Banuta',
  // Add more hunting spots as needed
};

// Store active claims
let activeClaims = {};

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

client.once('ready', () => {
  console.log(`Bot is ready! Logged in as ${client.user.tag}`);
});

client.on('messageCreate', async (message) => {
  if (message.author.bot) return;

  // Handle !resp command
  if (message.content.startsWith('!resp ')) {
    const huntCode = message.content.split(' ')[1]?.toLowerCase();
    
    if (!huntCode || !huntSpots[huntCode]) {
      message.reply('Invalid hunt code! Available codes: ' + Object.keys(huntSpots).join(', '));
      return;
    }

    // Check if already claimed
    if (activeClaims[huntCode]) {
      message.reply(`${huntSpots[huntCode]} is already claimed by ${activeClaims[huntCode].claimer}`);
      return;
    }

    // Claim the spot
    const claimer = message.author.displayName || message.author.username;
    const timestamp = new Date().toLocaleString();
    
    activeClaims[huntCode] = {
      claimer: claimer,
      timestamp: timestamp,
      userId: message.author.id
    };

    // Create embed
    const embed = new EmbedBuilder()
      .setTitle('🏹 Hunt Claimed!')
      .addFields(
        { name: 'Spot', value: huntSpots[huntCode], inline: true },
        { name: 'Claimed by', value: claimer, inline: true },
        { name: 'Time', value: timestamp, inline: true }
      )
      .setColor('#00ff00');

    // Find hunt-claims channel
    const claimsChannel = message.guild.channels.cache.find(
      channel => channel.name === 'hunt-claims'
    );

    if (claimsChannel) {
      claimsChannel.send({ embeds: [embed] });
      message.reply(`You claimed ${huntSpots[huntCode]}!`);
    } else {
      message.reply('Could not find #hunt-claims channel!');
    }
  }

  // Handle !unclaim command
  if (message.content.startsWith('!unclaim ')) {
    const huntCode = message.content.split(' ')[1]?.toLowerCase();
    
    if (!huntCode || !huntSpots[huntCode]) {
      message.reply('Invalid hunt code!');
      return;
    }

    if (!activeClaims[huntCode]) {
      message.reply(`${huntSpots[huntCode]} is not currently claimed.`);
      return;
    }

    // Check if user can unclaim (either the claimer or has manage messages permission)
    if (activeClaims[huntCode].userId !== message.author.id && 
        !message.member.permissions.has('ManageMessages')) {
      message.reply('You can only unclaim spots you claimed yourself!');
      return;
    }

    delete activeClaims[huntCode];
    message.reply(`${huntSpots[huntCode]} has been unclaimed.`);
  }

  // Handle !spots command
  if (message.content === '!spots') {
    let spotsList = 'Available hunt spots:\n';
    
    for (const [code, name] of Object.entries(huntSpots)) {
      const status = activeClaims[code] 
        ? `❌ Claimed by ${activeClaims[code].claimer}`
        : '✅ Available';
      spotsList += `**${code}** - ${name}: ${status}\n`;
    }

    message.reply(spotsList);
  }
});

client.login(process.env.DISCORD_BOT_TOKEN);
