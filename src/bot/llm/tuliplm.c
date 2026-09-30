#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

#include "tuliplm.h"

#define V 128
#define H 32
#define LR 0.01f

float W1[V][H], W2[H][V];

float sigmoid(float x)
{
    return 1.0f / (1.0f + expf(-x));
}

void init_model(void)
{
    srand(time(NULL));

    for (int i = 0; i < V; i++)
        for (int h = 0; h < H; h++)
            W1[i][h] =
                ((float)rand() / RAND_MAX - .5f) * .1f;

    for (int h = 0; h < H; h++)
        for (int i = 0; i < V; i++)
            W2[h][i] =
                ((float)rand() / RAND_MAX - .5f) * .1f;
}

void train_char(int input, int target)
{
    float h[H], o[V];

    for (int i = 0; i < H; i++)
        h[i] = sigmoid(W1[input][i]);

    for (int i = 0; i < V; i++)
    {
        o[i] = 0;

        for (int j = 0; j < H; j++)
            o[i] += h[j] * W2[j][i];

        o[i] = sigmoid(o[i]);
    }

    for (int j = 0; j < H; j++)
        for (int i = 0; i < V; i++)
            W2[j][i] -=
                LR * (o[i] - (i == target)) * h[j];

    for (int j = 0; j < H; j++)
    {
        float e = 0;

        for (int i = 0; i < V; i++)
            e += (o[i] - (i == target)) * W2[j][i];

        W1[input][j] -=
            LR * e * h[j] * (1 - h[j]);
    }
}

void learn(const char *text)
{
    for (int i = 0; text[i + 1]; i++)
        train_char(text[i], text[i + 1]);
}

void save_model(const char *filename)
{
    FILE *file = fopen(filename, "wb");

    if (!file)
        return;

    fwrite(W1, sizeof(W1), 1, file);
    fwrite(W2, sizeof(W2), 1, file);

    fclose(file);
}

void load_model(const char *filename)
{
    FILE *file = fopen(filename, "rb");

    if (!file)
    {
        init_model();
        return;
    }

    fread(W1, sizeof(W1), 1, file);
    fread(W2, sizeof(W2), 1, file);

    fclose(file);
}