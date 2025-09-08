const { Client, GatewayIntentBits, EmbedBuilder } = require('discord.js');
const fs = require('fs');

// Add Express keep-alive server for Replit
const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.send('Tibia Hunt Bot is running!');
});

app.listen(3000, () => {
  console.log('Keep-alive server running on port 3000');
});

// Hunt spot codes and names from the respawn list
const huntSpots = {
  // Ankrahmun
  'b17': 'Cobra Bastion',

  // Carlin
  'c5': 'Secret Library (Fire Area)',
  'c7': 'Secret Library (Energy Area)',

  // Cormaya
  'x2': 'Inqol -2',
  'x3': 'Inqol -3',

  // Darashia
  'd19': 'Ferumbra\'s Lair (Entrance)',
  'd20': 'Ferumbra\'s Plague Seal - 2',
  'd21': 'Ferumbra\'s Plague Seal - 1',
  'd22': 'Ferumbra\'s DT Seal',
  'd23': 'Ferumbra\'s Jugger Seal',
  'd24': 'Ferumbra\'s Fury Seal',
  'd25': 'Ferumbra\'s Undead Seal - 1',
  'd26': 'Ferumbra\'s Arc',
  'd27': 'Ferumbra\'s Pumin',
  'd28': 'Ferumbra\'s Fury Seal + 1',
  'd29': 'Ferumbra\'s Undead Seal - 2',

  // Edron
  'e29': 'Falcon Bastion',

  // Issavi
  'k12': 'Ruins of Nuur (Blu)',
  'k13': 'Salt Caves (Bashmu)',

  // Port Hope
  'p19': 'True Asura -1',
  'p20': 'True Asura -2',

  // Roshamuul
  'q3': 'Guzzlemaw Valley (East)',
  'q4': 'Guzzlemaw Valley (West)',

  // Venore
  't13': 'Flimsy -1',
  't14': 'Flimsy -2',

  // Warzone
  'u5': 'Warzone 3',
  'u16': 'Warzone 7 -1',
  'u17': 'Warzone 7 -2',
  'u18': 'Warzone 8'
};

// Game data structure
let gameData = {
  claims: {},
  players: {},
  timers: {},
  statusMessage: null,
  history: []
};

const DATA_FILE = 'huntData.json';

// Load data from file
function loadData() {
  try {
    if (fs.existsSync(DATA_FILE)) {
      const fileData = fs.readFileSync(DATA_FILE, 'utf8');
      const savedData = JSON.parse(fileData);

      gameData.claims = savedData.claims || {};
      gameData.players = savedData.players || {};
      gameData.timers = {};
      gameData.history = savedData.history || [];

      console.log('Game data loaded successfully');

      // Restore status message reference
      if (savedData.statusMessage) {
        const channel = client.channels.cache.get(savedData.statusMessage.channelId);
        if (channel) {
          channel.messages.fetch(savedData.statusMessage.messageId)
            .then(message => {
              gameData.statusMessage = message;
              console.log('Status message reference restored');
            })
            .catch(() => {
              console.log('Could not restore status message reference');
            });
        }
      }

      // Clear old timers and restart them
      for (const huntCode in gameData.claims) {
        const claim = gameData.claims[huntCode];
        if (claim.expiresAt > Date.now()) {
          startHuntTimer(huntCode, claim.expiresAt - Date.now());
        } else {
          expireHunt(huntCode);
        }
      }
    }
  } catch (error) {
    console.error('Error loading data:', error);
  }
}

// Save data to file
function saveData() {
  try {
    const dataToSave = {
      claims: gameData.claims,
      players: gameData.players,
      timers: {},
      history: gameData.history,
      statusMessage: gameData.statusMessage ? {
        channelId: gameData.statusMessage.channel.id,
        messageId: gameData.statusMessage.id
      } : null
    };
    fs.writeFileSync(DATA_FILE, JSON.stringify(dataToSave, null, 2));
  } catch (error) {
    console.error('Error saving data:', error);
  }
}

// Create live status board
async function createStatusBoard() {
  const respawnsChannel = client.channels.cache.find(
    channel => channel.name.toLowerCase() === 'respawns'
  );

  if (!respawnsChannel) {
    console.log('Could not find #respawns channel');
    return;
  }

  const embed = generateStatusEmbed();

  try {
    if (gameData.statusMessage) {
      await gameData.statusMessage.delete().catch(() => {});
    }

    const message = await respawnsChannel.send({ embeds: [embed] });
    gameData.statusMessage = message;
    saveData();

    console.log('Status board created successfully');
  } catch (error) {
    console.error('Error creating status board:', error);
  }
}

// Generate status embed
function generateStatusEmbed() {
  const embed = new EmbedBuilder()
    .setTitle('🏹 Tibia Hunt Respawns - Live Status')
    .setDescription('Live tracking of all hunting spots')
    .setColor('#2F3136')
    .setTimestamp();

  const cities = {
    'Ankrahmun': ['b17'],
    'Carlin': ['c5', 'c7'],
    'Cormaya': ['x2', 'x3'],
    'Darashia': ['d19', 'd20', 'd21', 'd22', 'd23', 'd24', 'd25', 'd26', 'd27', 'd28', 'd29'],
    'Edron': ['e29'],
    'Issavi': ['k12', 'k13'],
    'Port Hope': ['p19', 'p20'],
    'Roshamuul': ['q3', 'q4'],
    'Venore': ['t13', 't14'],
    'Warzone': ['u5', 'u16', 'u17', 'u18']
  };

  const cityNames = Object.keys(cities);

  // Create simple list format for each city
  for (const [city, codes] of Object.entries(cities)) {
    let cityDisplay = '';

    for (const code of codes) {
      const claim = gameData.claims[code];
      const huntName = huntSpots[code];

      if (claim) {
        const timeLeft = claim.expiresAt - Date.now();
        if (timeLeft > 0) {
          const hours = Math.floor(timeLeft / (1000 * 60 * 60));
          const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
          const user = client.users.cache.get(claim.claimedBy);
          const username = user ? (user.displayName || user.username) : 'Unknown';
          const queueInfo = claim.queue.length > 0 ? ` [+${claim.queue.length}]` : '';

          cityDisplay += `🔴 \`${code.toUpperCase()}\` **${huntName}**\n`;
          cityDisplay += `   ${username} - ${hours}h ${minutes}m${queueInfo}\n\n`;
        } else {
          cityDisplay += `🟢 \`${code.toUpperCase()}\` **${huntName}**\n`;
          cityDisplay += `   Available\n\n`;
        }
      } else {
        cityDisplay += `🟢 \`${code.toUpperCase()}\` **${huntName}**\n`;
        cityDisplay += `   Available\n\n`;
      }
    }

    // Handle Darashia specially - split it
    if (city === 'Darashia') {
      const firstHalf = codes.slice(0, 6);
      const secondHalf = codes.slice(6);

      let firstDisplay = '';
      let secondDisplay = '';

      // First half
      for (const code of firstHalf) {
        const claim = gameData.claims[code];
        const huntName = huntSpots[code];

        if (claim) {
          const timeLeft = claim.expiresAt - Date.now();
          if (timeLeft > 0) {
            const hours = Math.floor(timeLeft / (1000 * 60 * 60));
            const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
            const user = client.users.cache.get(claim.claimedBy);
            const username = user ? (user.displayName || user.username) : 'Unknown';
            const queueInfo = claim.queue.length > 0 ? ` [+${claim.queue.length}]` : '';

            firstDisplay += `🔴 \`${code.toUpperCase()}\` **${huntName}**\n`;
            firstDisplay += `   ${username} - ${hours}h ${minutes}m${queueInfo}\n\n`;
          } else {
            firstDisplay += `🟢 \`${code.toUpperCase()}\` **${huntName}**\n`;
            firstDisplay += `   Available\n\n`;
          }
        } else {
          firstDisplay += `🟢 \`${code.toUpperCase()}\` **${huntName}**\n`;
          firstDisplay += `   Available\n\n`;
        }
      }

      // Second half
      for (const code of secondHalf) {
        const claim = gameData.claims[code];
        const huntName = huntSpots[code];

        if (claim) {
          const timeLeft = claim.expiresAt - Date.now();
          if (timeLeft > 0) {
            const hours = Math.floor(timeLeft / (1000 * 60 * 60));
            const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
            const user = client.users.cache.get(claim.claimedBy);
            const username = user ? (user.displayName || user.username) : 'Unknown';
            const queueInfo = claim.queue.length > 0 ? ` [+${claim.queue.length}]` : '';

            secondDisplay += `🔴 \`${code.toUpperCase()}\` **${huntName}**\n`;
            secondDisplay += `   ${username} - ${hours}h ${minutes}m${queueInfo}\n\n`;
          } else {
            secondDisplay += `🟢 \`${code.toUpperCase()}\` **${huntName}**\n`;
            secondDisplay += `   Available\n\n`;
          }
        } else {
          secondDisplay += `🟢 \`${code.toUpperCase()}\` **${huntName}**\n`;
          secondDisplay += `   Available\n\n`;
        }
      }

      embed.addFields(
        {
          name: `🏰 ${city} (Part 1)`,
          value: firstDisplay,
          inline: false
        },
        {
          name: `🏰 ${city} (Part 2)`,
          value: secondDisplay,
          inline: false
        }
      );

      // Add separator after Darashia
      const isLastCity = city === cityNames[cityNames.length - 1];
      if (!isLastCity) {
        embed.addFields({
          name: '\u200B',
          value: '═══════════════════════════════════════',
          inline: false
        });
      }
    } else {
      embed.addFields({
        name: `🏰 ${city}`,
        value: cityDisplay,
        inline: false
      });

      // Add separator between cities (except for the last one)
      const isLastCity = city === cityNames[cityNames.length - 1];
      if (!isLastCity && city !== 'Darashia') {
        embed.addFields({
          name: '\u200B',
          value: '═══════════════════════════════════════',
          inline: false
        });
      }
    }
  }

  embed.setFooter({ text: 'Updates every minute • Use commands in #bot-commands' });

  return embed;
}

// Add to claim history (with duplicate prevention)
function addToHistory(huntCode, userId, userName, claimedAt, unclaimedAt) {
  // Check for recent duplicate entries (within 10 seconds)
  const recentDuplicate = gameData.history.find(entry => 
    entry.huntCode === huntCode &&
    entry.playerId === userId &&
    Math.abs(entry.claimedAt - claimedAt) < 10000
  );

  if (recentDuplicate) {
    console.log(`Prevented duplicate history entry for ${huntCode} by ${userName}`);
    return;
  }

  gameData.history.push({
    huntCode: huntCode,
    huntName: huntSpots[huntCode],
    playerId: userId,
    playerName: userName,
    claimedAt: claimedAt,
    unclaimedAt: unclaimedAt,
    duration: unclaimedAt - claimedAt
  });

  if (gameData.history.length > 100) {
    gameData.history = gameData.history.slice(-100);
  }
}

// Trigger immediate status board update
async function triggerStatusUpdate() {
  try {
    await updateStatusBoard();
  } catch (error) {
    console.error('Error triggering status update:', error);
  }
}

// Update status board
async function updateStatusBoard() {
  if (!gameData.statusMessage) {
    return;
  }

  try {
    const embed = generateStatusEmbed();
    await gameData.statusMessage.edit({ embeds: [embed] });
  } catch (error) {
    console.error('Error updating status board:', error);
    await createStatusBoard();
  }
}

// Timer management
function startHuntTimer(huntCode, duration) {
  if (gameData.timers[huntCode]) {
    clearTimeout(gameData.timers[huntCode]);
  }

  const claim = gameData.claims[huntCode];
  if (!claim) return;

  // Schedule 10 minute warning
  const tenMinWarning = Math.max(0, duration - 10 * 60 * 1000);
  if (tenMinWarning > 0) {
    setTimeout(() => {
      sendExpirationWarning(huntCode, 10);
    }, tenMinWarning);
  }

  // Schedule 5 minute warning
  const fiveMinWarning = Math.max(0, duration - 5 * 60 * 1000);
  if (fiveMinWarning > 0) {
    setTimeout(() => {
      sendExpirationWarning(huntCode, 5);
    }, fiveMinWarning);
  }

  // Schedule expiration
  gameData.timers[huntCode] = setTimeout(() => {
    expireHunt(huntCode);
  }, duration);
}

function sendExpirationWarning(huntCode, minutes) {
  const claim = gameData.claims[huntCode];
  if (!claim) return;

  const user = client.users.cache.get(claim.claimedBy);
  if (user) {
    user.send(`⚠️ Your hunt at **${huntSpots[huntCode]}** expires in **${minutes} minutes**!`);
  }
}

function expireHunt(huntCode) {
  const claim = gameData.claims[huntCode];
  if (!claim) return;

  const userId = claim.claimedBy;
  const user = client.users.cache.get(userId);
  const userName = user ? (user.displayName || user.username) : 'Unknown User';

  // Add to history when hunt expires naturally
  addToHistory(huntCode, userId, userName, claim.claimedAt, Date.now());

  if (user) {
    user.send(`⏰ Your hunt at **${huntSpots[huntCode]}** has expired.`);
  }

  if (!gameData.players[userId]) gameData.players[userId] = {};
  gameData.players[userId].currentClaim = null;
  gameData.players[userId].cooldownUntil = Date.now() + 10 * 60 * 1000;

  // Handle queue
  if (claim.queue && claim.queue.length > 0) {
    const nextUserId = claim.queue[0];
    const nextUser = client.users.cache.get(nextUserId);

    if (nextUser) {
      nextUser.send(`🎯 **${huntSpots[huntCode]}** is now available! You have 10 minutes to claim it with \`!resp ${huntCode}\` or you'll lose your spot.`);

      setTimeout(() => {
        const currentClaim = gameData.claims[huntCode];
        if (currentClaim && currentClaim.queue && currentClaim.queue[0] === nextUserId) {
          currentClaim.queue.shift();
          if (gameData.players[nextUserId]) {
            gameData.players[nextUserId].queuedFor = null;
          }
          nextUser.send(`❌ You didn't claim **${huntSpots[huntCode]}** in time and lost your spot.`);

          if (currentClaim.queue.length > 0) {
            expireHunt(huntCode);
          } else {
            delete gameData.claims[huntCode];
            saveData();
            triggerStatusUpdate();
          }
        }
      }, 10 * 60 * 1000);
    }
  } else {
    delete gameData.claims[huntCode];
  }

  if (gameData.timers[huntCode]) {
    clearTimeout(gameData.timers[huntCode]);
    delete gameData.timers[huntCode];
  }

  saveData();
  triggerStatusUpdate();
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.DirectMessages,
  ],
});

client.once('ready', () => {
  console.log(`Bot is ready! Logged in as ${client.user.tag}`);
  loadData();

  setTimeout(() => {
    createStatusBoard();
  }, 2000);

  setInterval(updateStatusBoard, 60000);
});

// Add error handling
client.on('error', error => {
  console.error('Discord client error:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  // Don't exit the process, just log the error
});

client.on('messageCreate', async (message) => {
  try {
    if (message.author.bot) return;

    const userId = message.author.id;
    
    // Check if message is a bot command
    const isCommand = message.content.startsWith('!help') || 
                     message.content.startsWith('!history') || 
                     message.content.startsWith('!resp ') || 
                     message.content.startsWith('!next ') || 
                     message.content === '!leave' || 
                     message.content === '!unclaim' || 
                     message.content === '!status' || 
                     message.content.startsWith('!queue ') || 
                     message.content === '!spots';

    // Delete command messages in guild channels
    if (isCommand && message.guild) {
      try {
        await message.delete();
      } catch (error) {
        console.log('Could not delete message:', error);
      }
    }

    // Function to send response (try DM first, fallback to channel mention)
    const sendResponse = async (content) => {
      try {
        await message.author.send(content);
      } catch (error) {
        // If DM fails and we're in a guild, send to channel with mention
        if (message.guild) {
          message.channel.send(`<@${userId}> ${content}`);
        } else {
          // If we're in DMs and can't send DM, log the error
          console.log('Could not send DM response:', error.message);
        }
      }
    };

    // Handle !help command
    if (message.content === '!help') {
      const helpMessage = `**Hunt Bot Commands:**

📍 **!spots** - Show all hunt spots and their status
🏹 **!resp [code]** - Claim a hunt spot (e.g., !resp b17)
🚪 **!unclaim** - Release your current hunt
⏭️ **!next [code]** - Join queue for claimed hunt
📊 **!status** - Check your hunt status and cooldown
🗂️ **!queue [code]** - See queue for a hunt spot
🚪 **!leave** - Leave your current hunt (10min cooldown)
📋 **!history** - View claim history (Admin only)
❓ **!help** - Show this help message

**Rules:**
• 3 hour hunt limit (auto-expires)
• 1 active hunt per player
• 1 queue position per player
• 10 minute cooldown after leaving/losing hunt
• Next player has 10 minutes to claim
• Live status available in #respawns`;

      await sendResponse(helpMessage);
      return;
    }

    // Handle !history command (Admin only)
    if (message.content.startsWith('!history')) {
      let isAdmin = false;
      if (message.guild) {
        isAdmin = message.member.permissions.has('Administrator');
      } else {
        // In DMs, check all guilds the bot is in to see if user is admin
        for (const guild of client.guilds.cache.values()) {
          try {
            const member = await guild.members.fetch(userId);
            if (member && member.permissions.has('Administrator')) {
              isAdmin = true;
              break;
            }
          } catch (error) {
            // User not in this guild, continue
          }
        }
      }

      if (!isAdmin) {
        await sendResponse('❌ This command requires Administrator permissions.');
        return;
      }

      if (message.content === '!history clean') {
        // Remove duplicate entries
        const uniqueHistory = [];
        const seen = new Set();

        for (const entry of gameData.history) {
          const key = `${entry.huntCode}-${entry.playerId}-${entry.claimedAt}`;
          if (!seen.has(key)) {
            seen.add(key);
            uniqueHistory.push(entry);
          }
        }

        const removedCount = gameData.history.length - uniqueHistory.length;
        gameData.history = uniqueHistory;
        saveData();

        await sendResponse(`🧹 Cleaned history: removed ${removedCount} duplicate entries. Total entries: ${uniqueHistory.length}`);
        return;
      }

      if (gameData.history.length === 0) {
        await sendResponse('📋 No claim history available yet.');
        return;
      }

      const recentHistory = gameData.history.slice(-10).reverse();

      let historyMsg = '📋 **Recent Hunt Claim History:**\n\n';

      recentHistory.forEach((entry, index) => {
        const claimedTime = new Date(entry.claimedAt).toLocaleString();
        const duration = Math.round(entry.duration / (1000 * 60));
        const durationHours = Math.floor(duration / 60);
        const durationMins = duration % 60;
        const durationText = durationHours > 0 ? `${durationHours}h ${durationMins}m` : `${durationMins}m`;

        historyMsg += `**${entry.huntCode.toUpperCase()}** ${entry.huntName}\n`;
        historyMsg += `👤 **${entry.playerName}** • ${claimedTime}\n`;
        historyMsg += `⏱️ Duration: **${durationText}**\n\n`;
      });

      historyMsg += '\n*Use `!history clean` to remove duplicates*';

      await sendResponse(historyMsg);
      return;
    }

    // Handle !resp command
    if (message.content.startsWith('!resp ')) {
      const huntCode = message.content.split(' ')[1]?.toLowerCase();

      if (!huntCode || !huntSpots[huntCode]) {
        await sendResponse('Invalid hunt code! Available codes: ' + Object.keys(huntSpots).join(', '));
        return;
      }

      const player = gameData.players[userId];
      if (player && player.cooldownUntil > Date.now()) {
        const cooldownLeft = Math.ceil((player.cooldownUntil - Date.now()) / 60000);
        await sendResponse(`You're on cooldown for **${cooldownLeft} minutes**. You cannot claim hunts yet.`);
        return;
      }

      if (player && player.currentClaim) {
        await sendResponse(`You already have **${huntSpots[player.currentClaim]}** claimed. Use \`!leave\` first.`);
        return;
      }

      const claim = gameData.claims[huntCode];
      if (claim) {
        if (claim.queue && claim.queue[0] === userId) {
          const claimedBy = claim.claimedBy;
          const claimedUser = client.users.cache.get(claimedBy);
          if (claimedUser) {
            claimedUser.send(`🔄 **${huntSpots[huntCode]}** has been claimed by the next player in queue.`);
          }
        } else {
          await sendResponse(`**${huntSpots[huntCode]}** is already claimed by <@${claim.claimedBy}>. Use \`!next ${huntCode}\` to join the queue.`);
          return;
        }
      }

      const now = Date.now();
      const expiresAt = now + 3 * 60 * 60 * 1000;

      if (claim && claim.queue) {
        claim.queue = claim.queue.filter(id => id !== userId);
      }

      gameData.claims[huntCode] = {
        claimedBy: userId,
        claimedAt: now,
        expiresAt: expiresAt,
        queue: claim ? claim.queue : []
      };

      if (!gameData.players[userId]) gameData.players[userId] = {};
      gameData.players[userId].currentClaim = huntCode;
      gameData.players[userId].cooldownUntil = 0;
      gameData.players[userId].queuedFor = null;

      startHuntTimer(huntCode, 3 * 60 * 60 * 1000);

      const claimer = message.author.displayName || message.author.username;
      const embed = new EmbedBuilder()
        .setTitle('🏹 Hunt Claimed!')
        .addFields(
          { name: 'Spot', value: huntSpots[huntCode], inline: true },
          { name: 'Claimed by', value: claimer, inline: true },
          { name: 'Expires', value: `<t:${Math.floor(expiresAt / 1000)}:R>`, inline: true }
        )
        .setColor('#00ff00');

      const claimsChannel = message.guild?.channels.cache.find(
        channel => channel.name === 'hunt-claims'
      );

      if (claimsChannel) {
        claimsChannel.send({ embeds: [embed] });
      }

      await sendResponse(`You claimed **${huntSpots[huntCode]}**! It expires in 3 hours.`);
      saveData();
      triggerStatusUpdate();
    }

    // Handle !next command
    if (message.content.startsWith('!next ')) {
      const huntCode = message.content.split(' ')[1]?.toLowerCase();

      if (!huntCode || !huntSpots[huntCode]) {
        await sendResponse('Invalid hunt code!');
        return;
      }

      const claim = gameData.claims[huntCode];
      if (!claim) {
        await sendResponse(`**${huntSpots[huntCode]}** is not currently claimed. Use \`!resp ${huntCode}\` to claim it.`);
        return;
      }

      const player = gameData.players[userId];
      if (player && player.currentClaim) {
        await sendResponse(`You already have **${huntSpots[player.currentClaim]}** claimed. You cannot queue for another hunt.`);
        return;
      }

      if (player && player.queuedFor) {
        await sendResponse(`You're already queued for **${huntSpots[player.queuedFor]}**. You can only queue for one hunt at a time.`);
        return;
      }

      if (claim.queue.includes(userId)) {
        const position = claim.queue.indexOf(userId) + 1;
        await sendResponse(`You're already in queue for **${huntSpots[huntCode]}** at position **${position}**.`);
        return;
      }

      claim.queue.push(userId);
      const position = claim.queue.length;

      if (!gameData.players[userId]) gameData.players[userId] = {};
      gameData.players[userId].queuedFor = huntCode;

      await sendResponse(`Added to queue for **${huntSpots[huntCode]}**! You're position **${position}** in line.`);
      saveData();
      triggerStatusUpdate();
    }

    // Handle !leave command
    if (message.content === '!leave') {
      const player = gameData.players[userId];
      if (!player || !player.currentClaim) {
        await sendResponse('You don\'t have any hunt claimed.');
        return;
      }

      const huntCode = player.currentClaim;
      const huntName = huntSpots[huntCode];
      const claim = gameData.claims[huntCode];
      const claimer = message.author.displayName || message.author.username;

      if (claim) {
        addToHistory(huntCode, userId, claimer, claim.claimedAt, Date.now());
      }

      player.currentClaim = null;
      player.cooldownUntil = Date.now() + 10 * 60 * 1000;

      const nextInQueue = claim?.queue?.[0];
      if (nextInQueue) {
        const nextUser = client.users.cache.get(nextInQueue);
        if (nextUser) {
          nextUser.send(`🎯 **${huntSpots[huntCode]}** is now available! You have 10 minutes to claim it with \`!resp ${huntCode}\` or you'll lose your spot.`);
        }
      }

      delete gameData.claims[huntCode];

      if (gameData.timers[huntCode]) {
        clearTimeout(gameData.timers[huntCode]);
        delete gameData.timers[huntCode];
      }

      saveData();
      triggerStatusUpdate();

      await sendResponse(`You left **${huntName}**. You have a 10 minute cooldown before claiming another hunt.`);
    }

    // Handle !unclaim command
    if (message.content === '!unclaim') {
      const player = gameData.players[userId];
      if (!player || !player.currentClaim) {
        await sendResponse('You don\'t have any hunt claimed.');
        return;
      }

      const huntCode = player.currentClaim;
      const huntName = huntSpots[huntCode];
      const claim = gameData.claims[huntCode];
      const claimer = message.author.displayName || message.author.username;

      if (claim) {
        addToHistory(huntCode, userId, claimer, claim.claimedAt, Date.now());
      }

      player.currentClaim = null;
      player.cooldownUntil = Date.now() + 10 * 60 * 1000;

      const nextInQueue = claim?.queue?.[0];
      if (nextInQueue) {
        const nextUser = client.users.cache.get(nextInQueue);
        if (nextUser) {
          nextUser.send(`🎯 **${huntSpots[huntCode]}** is now available! You have 10 minutes to claim it with \`!resp ${huntCode}\` or you'll lose your spot.`);
        }
      }

      delete gameData.claims[huntCode];

      if (gameData.timers[huntCode]) {
        clearTimeout(gameData.timers[huntCode]);
        delete gameData.timers[huntCode];
      }

      saveData();
      triggerStatusUpdate();

      await sendResponse(`You unclaimed **${huntName}**. You have a 10 minute cooldown before claiming another hunt.`);
    }

    // Handle !status command
    if (message.content === '!status') {
      const player = gameData.players[userId];
      let statusMsg = '**Your Status:**\n';

      if (player && player.currentClaim) {
        const claim = gameData.claims[player.currentClaim];
        const timeLeft = Math.ceil((claim.expiresAt - Date.now()) / 60000);
        statusMsg += `🏹 Currently hunting: **${huntSpots[player.currentClaim]}**\n`;
        statusMsg += `⏰ Time left: **${Math.floor(timeLeft / 60)}h ${timeLeft % 60}m**\n`;
      } else {
        statusMsg += '🏹 No active hunt\n';
      }

      if (player && player.queuedFor) {
        const queueClaim = gameData.claims[player.queuedFor];
        if (queueClaim) {
          const position = queueClaim.queue.indexOf(userId) + 1;
          statusMsg += `📝 Queued for: **${huntSpots[player.queuedFor]}** (position ${position})\n`;
        }
      }

      if (player && player.cooldownUntil > Date.now()) {
        const cooldownLeft = Math.ceil((player.cooldownUntil - Date.now()) / 60000);
        statusMsg += `❄️ Cooldown: **${cooldownLeft} minutes** remaining`;
      } else {
        statusMsg += '✅ No cooldown - ready to hunt!';
      }

      await sendResponse(statusMsg);
    }

    // Handle !queue command
    if (message.content.startsWith('!queue ')) {
      const huntCode = message.content.split(' ')[1]?.toLowerCase();

      if (!huntCode || !huntSpots[huntCode]) {
        await sendResponse('Invalid hunt code!');
        return;
      }

      const claim = gameData.claims[huntCode];
      if (!claim) {
        await sendResponse(`**${huntSpots[huntCode]}** is not currently claimed.`);
        return;
      }

      let queueMsg = `**Queue for ${huntSpots[huntCode]}:**\n`;
      queueMsg += `🏹 Current: <@${claim.claimedBy}>\n`;

      if (claim.queue.length === 0) {
        queueMsg += '📝 Queue is empty';
      } else {
        queueMsg += '📝 Queue:\n';
        claim.queue.forEach((queueUserId, index) => {
          queueMsg += `  ${index + 1}. <@${queueUserId}>\n`;
        });
      }

      await sendResponse(queueMsg);
    }

    // Handle !spots command
    if (message.content === '!spots') {
      let spotsList = '**Available Hunt Spots:**\n\n';

      const cities = {
        'Ankrahmun': ['b17'],
        'Carlin': ['c5', 'c7'],
        'Cormaya': ['x2', 'x3'],
        'Darashia': ['d19', 'd20', 'd21', 'd22', 'd23', 'd24', 'd25', 'd26', 'd27', 'd28', 'd29'],
        'Edron': ['e29'],
        'Issavi': ['k12', 'k13'],
        'Port Hope': ['p19', 'p20'],
        'Roshamuul': ['q3', 'q4'],
        'Venore': ['t13', 't14'],
        'Warzone': ['u5', 'u16', 'u17', 'u18']
      };

      for (const [city, codes] of Object.entries(cities)) {
        spotsList += `**${city}:**\n`;
        for (const code of codes) {
          const claim = gameData.claims[code];
          let status;
          if (claim) {
            const timeLeft = Math.ceil((claim.expiresAt - Date.now()) / 60000);
            const queueInfo = claim.queue.length > 0 ? ` (${claim.queue.length} in queue)` : '';
            status = `❌ Claimed by <@${claim.claimedBy}> - ${Math.floor(timeLeft / 60)}h ${timeLeft % 60}m left${queueInfo}`;
          } else {
            status = '✅ Available';
          }
          spotsList += `  **${code}** - ${huntSpots[code]}: ${status}\n`;
        }
        spotsList += '\n';
      }

      await sendResponse(spotsList);
    }

  } catch (error) {
    console.error('Error in messageCreate handler:', error);
    // Try to respond to the user about the error
    try {
      if (message.guild) {
        message.channel.send(`<@${message.author.id}> Sorry, there was an error processing your command.`);
      } else {
        message.author.send('Sorry, there was an error processing your command.');
      }
    } catch (sendError) {
      console.error('Could not send error message to user:', sendError);
    }
  }
});

client.login(process.env.DISCORD_BOT_TOKEN);
