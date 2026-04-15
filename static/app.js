const generateBtn = document.getElementById("generateBtn");
const randomPuzzleBtn = document.getElementById("randomPuzzleBtn");
const submitBtn = document.getElementById("submitBtn");
const resetBtn = document.getElementById("resetBtn");
const showAnswerBtn = document.getElementById("showAnswerBtn");

const statusBox = document.getElementById("statusBox");
const placedCountEl = document.getElementById("placedCount");
const filledBucketsEl = document.getElementById("filledBuckets");
const modeTextEl = document.getElementById("modeText");

const bankGrid = document.getElementById("bankGrid");
const wordBankDropzone = document.getElementById("wordBankDropzone");
const bucketGrid = document.getElementById("bucketGrid");

const BUCKET_COUNT = 4;
const BUCKET_SIZE = 4;

let puzzleData = null;
let originalGrid = [];
let bankWords = [];
let buckets = [[], [], [], []];
let revealedCategories = [null, null, null, null];
let correctBuckets = [false, false, false, false];
let dragInfo = null;

function setStatus(message, type = "") {
  statusBox.className = "status";
  if (type) statusBox.classList.add(type);
  statusBox.textContent = message;
}

function normalizeGroup(words) {
  return [...words].map(w => w.trim().toUpperCase()).sort().join("||");
}

function arraysEqualIgnoreOrder(a, b) {
  return normalizeGroup(a) === normalizeGroup(b);
}

function countPlaced() {
  return buckets.reduce((sum, bucket) => sum + bucket.length, 0);
}

function countFilledBuckets() {
  return buckets.filter(bucket => bucket.length === BUCKET_SIZE).length;
}

function sortByOriginalOrder(words) {
  const order = new Map(originalGrid.map((word, index) => [word, index]));
  return [...words].sort((a, b) => (order.get(a) ?? 9999) - (order.get(b) ?? 9999));
}

function resetBoardState() {
  bankWords = [...originalGrid];
  buckets = [[], [], [], []];
  revealedCategories = [null, null, null, null];
  correctBuckets = [false, false, false, false];
  dragInfo = null;
}

function updateSummary() {
  placedCountEl.textContent = `${countPlaced()}/16`;
  filledBucketsEl.textContent = `${countFilledBuckets()}/4`;

  if (!puzzleData) {
    modeTextEl.textContent = "Idle";
  } else {
    modeTextEl.textContent = "Playing";
  }

  const allPlaced = countPlaced() === 16;
  submitBtn.disabled = !puzzleData || !allPlaced;
  resetBtn.disabled = !puzzleData;
  showAnswerBtn.disabled = !puzzleData;
}

function createTile(word, sourceType, bucketIndex = null) {
  const tile = document.createElement("div");
  tile.className = "tile";
  tile.textContent = word;
  tile.draggable = true;

  tile.addEventListener("dragstart", () => {
    dragInfo = {
      word,
      sourceType,
      bucketIndex
    };
  });

  return tile;
}

function renderBank() {
  bankGrid.innerHTML = "";

  if (!bankWords.length) {
    const empty = document.createElement("div");
    empty.className = "empty-note";
    // empty.textContent = "All words have been placed in the containers below.";
    bankGrid.appendChild(empty);
    return;
  }

  bankWords.forEach(word => {
    bankGrid.appendChild(createTile(word, "bank"));
  });
}

function renderBuckets() {
  bucketGrid.innerHTML = "";

  for (let i = 0; i < BUCKET_COUNT; i++) {
    const bucket = document.createElement("div");
    bucket.className = "bucket";
    if (correctBuckets[i]) bucket.classList.add("correct");

    bucket.addEventListener("dragover", (e) => {
      e.preventDefault();
    });

    bucket.addEventListener("dragenter", (e) => {
      e.preventDefault();
      bucket.classList.add("drag-over");
    });

    bucket.addEventListener("dragleave", () => {
      bucket.classList.remove("drag-over");
    });

    bucket.addEventListener("drop", (e) => {
      e.preventDefault();
      bucket.classList.remove("drag-over");
      dropIntoBucket(i);
    });

    const head = document.createElement("div");
    head.className = "bucket-head";

    const headLeft = document.createElement("div");

    const label = document.createElement("div");
    label.className = "bucket-label";
    label.textContent = `Container ${i + 1}`;

    const category = document.createElement("div");
    category.className = "bucket-category";
    category.textContent = revealedCategories[i] || "Waiting for category...";

    headLeft.appendChild(label);
    headLeft.appendChild(category);

    const count = document.createElement("div");
    count.className = "bucket-count";
    count.textContent = `${buckets[i].length}/${BUCKET_SIZE}`;

    head.appendChild(headLeft);
    head.appendChild(count);

    const slots = document.createElement("div");
    slots.className = "bucket-slots";

    buckets[i].forEach(word => {
      slots.appendChild(createTile(word, "bucket", i));
    });

    for (let k = buckets[i].length; k < BUCKET_SIZE; k++) {
      const placeholder = document.createElement("div");
      placeholder.className = "placeholder";
      placeholder.textContent = "Drop Here";
      slots.appendChild(placeholder);
    }

    bucket.appendChild(head);
    bucket.appendChild(slots);

    bucketGrid.appendChild(bucket);
  }
}

function renderMetadata() {
    return
}

function renderAll() {
  renderBank();
  renderBuckets();
  renderMetadata();
  updateSummary();
}

function dropIntoBucket(targetBucketIndex) {
  if (!dragInfo) return;

  const { word, sourceType, bucketIndex } = dragInfo;

  if (sourceType === "bank") {
    if (buckets[targetBucketIndex].length >= BUCKET_SIZE) return;
    if (!bankWords.includes(word)) return;

    bankWords = bankWords.filter(w => w !== word);
    buckets[targetBucketIndex].push(word);
  } else if (sourceType === "bucket") {
    if (bucketIndex === targetBucketIndex) return;
    if (buckets[targetBucketIndex].length >= BUCKET_SIZE) return;

    buckets[bucketIndex] = buckets[bucketIndex].filter(w => w !== word);
    buckets[targetBucketIndex].push(word);
  }

  revealedCategories = [null, null, null, null];
  correctBuckets = [false, false, false, false];

  setStatus("Continue adjusting your groups, then click Submit.", "info");
  renderAll();
}

function dropBackToBank() {
  if (!dragInfo) return;
  if (dragInfo.sourceType !== "bucket") return;

  const { word, bucketIndex } = dragInfo;
  buckets[bucketIndex] = buckets[bucketIndex].filter(w => w !== word);
  bankWords = sortByOriginalOrder([...bankWords, word]);

  revealedCategories = [null, null, null, null];
  correctBuckets = [false, false, false, false];

  setStatus("Word has been moved back to the word bank.", "info");
  renderAll();
}

function resetBoard() {
  if (!puzzleData) return;
  resetBoardState();
  setStatus("Board has been reset, all words returned to their initial positions.", "info");
  renderAll();
}

function submitBoard() {
  if (!puzzleData) return;

  const allFull = buckets.every(bucket => bucket.length === BUCKET_SIZE);
  if (!allFull) {
    setStatus("Four containers must each contain exactly 4 words.", "warn");
    return;
  }

  const matchedCategories = buckets.map(bucket => {
    const matched = puzzleData.puzzle.find(group =>
      arraysEqualIgnoreOrder(group.words, bucket)
    );
    return matched ? matched.category : null;
  });

  revealedCategories = matchedCategories;
  correctBuckets = matchedCategories.map(Boolean);

  const matchedCount = correctBuckets.filter(Boolean).length;

  if (matchedCount === 4) {
    setStatus("Congratulations, all four groups are correct. The category is displayed above the corresponding container.", "success");
    modeTextEl.textContent = "Solved";
  } else {
    setStatus(`Currently, ${matchedCount}/4 containers are completely correct. You can continue trying, or click Show Answer.`, "warn");
  }

  renderAll();
}

function showAnswer() {
  if (!puzzleData) return;

  buckets = puzzleData.puzzle.map(group => [...group.words]);
  bankWords = [];
  revealedCategories = puzzleData.puzzle.map(group => group.category);
  correctBuckets = [true, true, true, true];

  setStatus("Correct answers have been revealed.", "info");
  modeTextEl.textContent = "Revealed";
  renderAll();
}

async function loadPuzzle(apiPath, loadingMessage, successMessage) {
  try {
    setStatus(loadingMessage, "info");
    modeTextEl.textContent = "Loading";

    generateBtn.disabled = true;
    randomPuzzleBtn.disabled = true;
    submitBtn.disabled = true;
    resetBtn.disabled = true;
    showAnswerBtn.disabled = true;

    const res = await fetch(apiPath, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      }
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Unknown error");
    }

    if (!data.shuffled_grid || data.shuffled_grid.length !== 16) {
      throw new Error("The backend returned a shuffled_grid that is not 16 words long.");
    }

    puzzleData = data;
    originalGrid = [...data.shuffled_grid];
    resetBoardState();

    setStatus(successMessage, "info");
    renderAll();
  } catch (err) {
    console.error(err);
    setStatus(`Failed to load puzzle: ${err.message}`, "error");
    modeTextEl.textContent = "Error";
  } finally {
    generateBtn.disabled = false;
    randomPuzzleBtn.disabled = false;
    updateSummary();
  }
}

async function generatePuzzle() {
  await loadPuzzle(
    "/api/generate-puzzle",
    "Generating puzzle...",
    "Puzzle generated. Please drag the 16 words to the four containers below."
  );
}

async function loadRandomPrebuiltPuzzle() {
  await loadPuzzle(
    "/api/random-puzzle",
    "Loading random puzzle...",
    "Random puzzle loaded. Please drag the 16 words to the four containers below."
  );
}

wordBankDropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
});

wordBankDropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropBackToBank();
});

generateBtn.addEventListener("click", generatePuzzle);
randomPuzzleBtn.addEventListener("click", loadRandomPrebuiltPuzzle);
submitBtn.addEventListener("click", submitBoard);
resetBtn.addEventListener("click", resetBoard);
showAnswerBtn.addEventListener("click", showAnswer);

renderAll();